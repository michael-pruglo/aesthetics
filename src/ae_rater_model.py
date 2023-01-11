import logging
import os
import statistics
import numpy as np
from typing import Callable

from ae_rater_types import *
from db_managers import MetadataManager, HistoryManager
from prioritizers import PrioritizerType
from rating_backends import RatingBackend, ELO, Glicko
from helpers import short_fname

# make default_values work
# make history replay work
# add diagnostic info


class RatingCompetition:
  def __init__(self):
    self.rat_systems:list[RatingBackend] = [Glicko(), ELO()]

  def get_sysnames(self) -> list[RatSystemName]:
    return [s.name() for s in self.rat_systems]

  def consume_match(self, match:MatchInfo) -> tuple[RatingOpinions, str]:
    logging.info("exec")
    logging.info("consume_match outcome = '%s'  boosts = %s", match.outcome.tiers, match.outcome.boosts)
    opinions = {s.name(): s.process_match(match)
                for s in self.rat_systems}
    logging.info("opinions:\n%s", self._pretty_opinions(match.profiles, opinions, match.outcome))
    return opinions, "diagnostic"

  def _pretty_opinions(self, participants:list[ProfileInfo], opinions:RatingOpinions, outcome:Outcome) -> str:
    s = ""
    for letter in outcome.tiers:
      if letter.isspace():
        s += "\n\n"
      else:
        idx = Outcome.let_to_idx(letter)
        s += f"\t{letter} {participants[idx]}  "
        for system, changes in opinions.items():
          s += f"{system}: {changes[idx]} "
        s += "\n"
    return s

  def _confidence_markers(self, opinions:RatingOpinions) -> str:
    avg_changes = {sname: statistics.mean([abs(ch.delta_rating) for ch in changes])
                   for sname,changes in opinions.items()}
    rd_improvements = {}
    for system, changes in opinions.items():
        sys_rd = statistics.mean([prof.ratings[system].rd-change.new_rating.rd
                                  for prof, change in zip(self.curr_match, changes)])
        rd_improvements[system] = sys_rd
    return f"average_changes: {avg_changes}\nrd_improvements: {rd_improvements}\n"





class RatingCompetitionOLD:
  def __init__(self, img_dir:str, refresh:bool):
    self.curr_match:list[ProfileInfo] = []
    self.rat_systems:list[RatingBackend] = [Glicko(), ELO()]
    def default_values_getter(stars:float)->dict:
      default_values = {}
      for s in self.rat_systems:
        default_values.update(s.get_default_values(stars))
      return default_values
    self.db = DBAccess(img_dir, refresh, default_values_getter,
                       [s.name() for s in self.rat_systems])



  def give_boost(self, short_name:str, mult:int) -> None:
    profile = self.db.retreive_profile(short_name)
    logging.info("boost %+dx %s", mult, profile)

    self.db.apply_opinions(
      [profile],
      {s.name(): [s.get_boost(profile, mult)] for s in self.rat_systems},
    )
    self._refresh_curr_match()

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    shname = short_fname(fullname)
    logging.info("model.update_meta for %s:\n %s", shname, meta)
    db_row = self.db.retreive_profile(shname)
    if int(db_row.stars) == meta.stars:
      meta.stars = None
    self.db.update_meta(fullname, meta)
    self._refresh_curr_match()



class Analyzer:
  def consume_diagnostic(self, diagnostic_info):
    logging.info("exec %s", diagnostic_info)
    pass


class DBAccess:
  def __init__(self, media_dir, refresh, prioritizer_type=PrioritizerType.DEFAULT) -> None:
    self.media_dir = media_dir
    self.meta_mgr = MetadataManager(media_dir, refresh, prioritizer_type)
    self.history_mgr = HistoryManager(media_dir)
    self.sysnames = []

  def set_sysnames(self, sysnames:list[RatSystemName]) -> None:
    self.sysnames = sysnames

  def set_prioritizer(self, prioritizer_type) -> None:
    self.meta_mgr.set_prioritizer(prioritizer_type)

  def save_match(self, match:MatchInfo) -> None:
    logging.info("exec")
    self.history_mgr.save_match(
      match.timestamp,
      [short_fname(p.fullname) for p in match.profiles],
      match.outcome.tiers,  # maybe save boosts as well?
    )

  def get_match_history(self) -> list[MatchInfo]:
    logging.info("exec")
    return [MatchInfo(p,o,t) for t,p,o in self.history_mgr.get_match_history().iterrows()]

  def apply_opinions(self, profiles:list[ProfileInfo], opinions:RatingOpinions) -> None:
    logging.info("exec")
    for i,prof in enumerate(profiles):
      new_ratings = {}
      proposed_stars = []
      for sysname,changes in opinions.items():
        proposed_stars.append(changes[i].new_stars)
        new_ratings.update({
          sysname+'_pts': changes[i].new_rating.points,
          sysname+'_rd': changes[i].new_rating.rd,
          sysname+'_time': changes[i].new_rating.timestamp,
        })
      new_ratings['stars'] = statistics.mean(proposed_stars)

      self.meta_mgr.update(prof.fullname, new_ratings, len(profiles)-1)

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    logging.info("exec")
    db_prof = self.get_profile(fullname)
    if int(db_prof.stars) == meta.stars:
      meta.stars = None

    upd = {}
    if meta.tags is not None:
      upd['tags'] = ' '.join(sorted(meta.tags)).lower()
    if meta.stars is not None:
      upd['stars'] = meta.stars
      upd |= self.def_gettr(meta.stars)
    if meta.awards is not None:
      upd['awards'] = ' '.join(sorted(meta.awards)).lower()
    self.meta_mgr.update(fullname, upd_data=upd)

  def get_leaderboard(self) -> list[ProfileInfo]:
    logging.info("exec")
    db = self.meta_mgr.get_db()
    db.sort_values('stars', ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

  def get_next_match(self, n:int) -> list[ProfileInfo]:
    logging.info("exec")
    sample = self.meta_mgr.get_rand_files_info(n)
    return [self._validate_and_convert_info(sample.iloc[i])
            for i in range(len(sample))]

  def get_search_results(self, query:str) -> list[ProfileInfo]:
    logging.info("exec")
    hits = self.meta_mgr.get_search_results(query)
    return [self._validate_and_convert_info(hits.iloc[i])
            for i in range(len(hits))]

  def get_profile(self, fullname:str) -> ProfileInfo:
    logging.info("exec")
    info = self.meta_mgr.get_file_info(short_fname(fullname))
    return self._validate_and_convert_info(info)

  def get_tags_vocab(self) -> list[str]:
    logging.info("exec")
    return self.meta_mgr.get_tags_vocab()

  def on_exit(self) -> None:
    logging.info("exec")
    self.meta_mgr.on_exit()

  def _validate_and_convert_info(self, info) -> ProfileInfo:
    short_name = info.name

    expected_dtypes = {
      'tags': str,
      'stars': np.float64,
      'nmatches': np.int64,
      'priority': np.float64,
      'awards': str,
    }
    for sname in self.sysnames:
      expected_dtypes |= {
        sname+'_pts': np.int64,
        sname+'_rd': np.int64,
        sname+'_time': np.float64,
      }
    assert all(col in info.index for col in expected_dtypes.keys()), str(info)
    assert 0 <= info['stars']
    for col,t in expected_dtypes.items():
      assert isinstance(info[col], t), f"{col} expected {t}  got {type(info[col])} {short_name}"

    return ProfileInfo(
      tags=info['tags'],
      fullname=os.path.join(self.media_dir, short_name),
      stars=info['stars'],
      ratings={sname:Rating(info[sname+'_pts'], info[sname+'_rd'], info[sname+'_time'])
               for sname in self.sysnames},
      nmatches=int(info['nmatches']),
      awards=info['awards'],
    )


class DBAccessOLD:
  def __init__(self, img_dir:str, refresh:bool, prioritizer_type,
               default_values_getter:Callable[[int],dict], sysnames:list[str]) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, prioritizer_type, default_values_getter)
    self.def_gettr = default_values_getter
    self.history_mgr = HistoryManager(img_dir)
    self.sysnames = sysnames

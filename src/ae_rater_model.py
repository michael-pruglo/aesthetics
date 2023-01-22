import logging
import os
import statistics
import numpy as np

from ae_rater_types import *
from db_managers import MetadataManager, HistoryManager
from rating_backends import RatingBackend, ELO, Glicko
from helpers import short_fname

# make history replay work
# add diagnostic info


class RatingCompetition:
  def __init__(self):
    self.rat_systems:list[RatingBackend] = [Glicko(), ELO()]

  def get_rat_systems(self) -> list[RatingBackend]:
    return self.rat_systems

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


class Analyzer:
  def consume_diagnostic(self, diagnostic_info):
    logging.info("exec %s", diagnostic_info)
    pass


class DBAccess:
  def __init__(self, media_dir, refresh, prioritizer_type, rat_systems:list[RatingBackend]) -> None:
    self.media_dir = media_dir
    self.rat_systems = rat_systems
    self.meta_mgr = MetadataManager(media_dir, refresh, prioritizer_type, self.default_values_getter)
    self.history_mgr = HistoryManager(media_dir)

  def default_values_getter(self, stars:float)->dict:
    default_values = {}
    for s in self.rat_systems:
      def_rat = s.stars_to_rating(stars)
      default_values.update({
        s.name()+"_pts": def_rat.points,
        s.name()+"_rd": def_rat.rd,
        s.name()+"_time": def_rat.timestamp,
      })
    return default_values

  def save_match(self, match:MatchInfo) -> None:
    logging.info("exec")
    self.history_mgr.save_match(
      match.timestamp,
      [short_fname(p.fullname) for p in match.profiles],
      match.outcome.tiers,  # maybe save boosts as well?
    )

  def get_match_history(self) -> list[MatchInfo]:
    logging.info("exec")
    hist = []
    for index, (timestamp, names, outcome_str) in self.history_mgr.get_match_history().iterrows():
      assert isinstance(timestamp, float)
      assert isinstance(names, list)
      assert isinstance(outcome_str, str)
      profiles = [self.get_profile(os.path.join(self.media_dir,shname)) for shname in names]
      hist.append(MatchInfo(profiles, Outcome(outcome_str), timestamp))
    return hist

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
      upd |= self.default_values_getter(meta.stars)
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
    for s in self.rat_systems:
      expected_dtypes |= {
        s.name()+'_pts': np.int64,
        s.name()+'_rd': np.int64,
        s.name()+'_time': np.float64,
      }
    assert all(col in info.index for col in expected_dtypes.keys()), str(info)
    assert 0 <= info['stars']
    for col,t in expected_dtypes.items():
      assert isinstance(info[col], t), f"{col} expected {t}  got {type(info[col])} {short_name}"

    return ProfileInfo(
      tags=info['tags'],
      fullname=os.path.join(self.media_dir, short_name),
      stars=info['stars'],
      ratings={s.name():Rating(info[s.name()+'_pts'], info[s.name()+'_rd'], info[s.name()+'_time'])
               for s in self.rat_systems},
      nmatches=int(info['nmatches']),
      awards=info['awards'],
    )

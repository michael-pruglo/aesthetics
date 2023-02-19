import logging
import os
import statistics
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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

  def consume_match(self, match:MatchInfo) -> tuple[RatingOpinions, DiagnosticInfo]:
    logging.info("consume_match outcome = '%s'  boosts = %s", match.outcome.tiers, match.outcome.boosts)
    opinions = {s.name(): s.process_match(match)
                for s in self.rat_systems}
    logging.info("opinions:\n%s", self._pretty_opinions(match.profiles, opinions, match.outcome))
    diagnostic = self._confidence_markers(match, opinions)
    logging.info("diagnostic:\n%s", diagnostic)
    return opinions, diagnostic

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

  def _confidence_markers(self, match:MatchInfo, opinions:RatingOpinions) -> DiagnosticInfo:
    info = {}
    info['timestamp'] = match.timestamp
    for sname,changes in opinions.items():
      info['avg_change_'+sname] = statistics.mean([abs(ch.delta_rating) for ch in changes])
      info['rd_improve_'+sname] = statistics.mean([prof.ratings[sname].rd-change.new_rating.rd
                                  for prof, change in zip(match.profiles, changes)])
    return pd.Series(info)


class Analyzer:
  def __init__(self) -> None:
    self.df = None

  def consume_diagnostic(self, diagnostic_info:DiagnosticInfo):
    if self.df is None:
      self.df = pd.DataFrame([diagnostic_info])
    else:
      self.df.loc[len(self.df)] = diagnostic_info

  def show_results(self):
    if self.df is None:
      return
    self.df.plot(subplots=True, figsize=(10,10))
    plt.title("Diagnostic of the replay")
    plt.show()


class DBAccess:
  def __init__(self, media_dir, refresh, prioritizer_type, rat_systems:list[RatingBackend], history_fname:str) -> None:
    self.media_dir = media_dir
    self.rat_systems = rat_systems
    self.meta_mgr = MetadataManager(media_dir, refresh, prioritizer_type, self.default_values_getter)
    self.history_mgr = HistoryManager(media_dir, history_fname)

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
    self.history_mgr.save_match(
      match.timestamp,
      str([short_fname(p.fullname) for p in match.profiles]),
      match.outcome.rawstr
    )

  def reset_meta_to_initial(self) -> None:
    self.meta_mgr.reset_meta_to_initial()

  def get_match_history(self) -> list[MatchInfo]:
    hist = []
    matches_unavailable = 0
    for index, (timestamp, names, outcome_str) in self.history_mgr.get_match_history().iterrows():
      assert isinstance(timestamp, float)
      assert isinstance(names, str), type(names)
      assert names
      names = eval(names)
      assert isinstance(names, list)
      assert isinstance(outcome_str, str)
      try:
        profiles = [self.get_profile(os.path.join(self.media_dir,shname)) for shname in names]
        hist.append(MatchInfo(profiles, Outcome(outcome_str), timestamp))
      except KeyError:
        matches_unavailable += 1

    if matches_unavailable:
      logging.warning(f"get_match_history: couldn't reconstruct {matches_unavailable} matches")
    return hist

  def apply_opinions(self, profiles:list[ProfileInfo], opinions:RatingOpinions) -> None:
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
    db_prof = self.get_profile(fullname)
    starchange = int(db_prof.stars)!=meta.stars
    upd = {
      'tags': ' '.join(meta.tags).lower(),
      'stars': meta.stars if starchange else db_prof.stars,
      'awards': ' '.join(meta.awards).lower(),
    }
    if starchange:
      upd |= self.default_values_getter(meta.stars)
    self.meta_mgr.update(fullname, upd)

  def get_leaderboard(self) -> list[ProfileInfo]:
    db = self.meta_mgr.get_db()
    sortpriorities = ['stars'] + [s.name()+'_pts' for s in self.rat_systems] + ['awards']
    db.sort_values(sortpriorities, ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

  def get_next_match(self, n:int) -> list[ProfileInfo]:
    sample = self.meta_mgr.get_rand_files_info(n)
    return [self._validate_and_convert_info(sample.iloc[i])
            for i in range(len(sample))]

  def get_search_results(self, query:str) -> list[ProfileInfo]:
    hits = self.meta_mgr.get_search_results(query)
    return [self._validate_and_convert_info(hits.iloc[i])
            for i in range(len(hits))]

  def get_profile(self, fullname:str) -> ProfileInfo:
    info = self.meta_mgr.get_file_info(short_fname(fullname))
    return self._validate_and_convert_info(info)

  def on_exit(self) -> None:
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

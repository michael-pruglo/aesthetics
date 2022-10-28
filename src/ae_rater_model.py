import logging
import os
import statistics
import time
import numpy as np
from typing import Callable

from ae_rater_types import *
from db_managers import MetadataManager, HistoryManager
from metadata import write_metadata
from rating_backends import RatingBackend, ELO, Glicko
from helpers import short_fname


class RatingCompetition:
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

  def get_search_results(self, query:str) -> list[ProfileInfo]:
    return self.db.get_search_results(query)

  def get_curr_match(self) -> list[ProfileInfo]:
    return self.curr_match

  def generate_match(self, n:int=2) -> list[ProfileInfo]:
    self.curr_match = self.db.retreive_rand_profiles(n)
    return self.curr_match

  def get_leaderboard(self) -> list[ProfileInfo]:
    return self.db.get_leaderboard(sortpriority=['stars']+[s.name()+"_pts" for s in self.rat_systems])

  def get_tags_vocab(self) -> list[str]:
    return self.db.get_tags_vocab()

  def consume_result(self, outcome:Outcome) -> RatingOpinions:
    logging.info("consume_result outcome = %s", outcome.tiers)
    self.db.save_match(self.curr_match, outcome)

    opinions = {s.name(): s.process_match(self.curr_match, outcome)
                for s in self.rat_systems}
    logging.info("opinions:\n%s", self._pretty_opinions(opinions, outcome))
    self.db.apply_opinions(self.curr_match, opinions)

    self.curr_match = []
    return opinions

  def give_boost(self, short_name:str, mult:int) -> None:
    profile = self.db.retreive_profile(short_name)
    logging.info("boost %+dx %s", mult, profile)

    self.db.apply_opinions(
      [profile],
      {s.name(): [s.get_boost(profile, mult)] for s in self.rat_systems},
    )
    self._refresh_curr_match()

  def update_meta(self, fullname:str, tags:list[str]=None, stars:int=None) -> None:
    logging.info("update meta on disk: %s  %s %d", short_fname(fullname), tags, stars)
    self.db.update_meta(fullname, tags, stars)
    self._refresh_curr_match()

  def give_awards(self, fullname:str, awards:list[str]) -> None:
    logging.info(f"award {short_fname(fullname)} with '{awards}'")
    self.db.give_awards(fullname, awards)

  def on_exit(self):
    self.db.on_exit()

  def _pretty_opinions(self, opinions:RatingOpinions, outcome:Outcome) -> str:
    s = ""
    for letter in outcome.tiers:
      if letter.isspace():
        s += "\n\n"
      else:
        idx = Outcome.let_to_idx(letter)
        s += f"\t{letter} {self.curr_match[idx]}  "
        for system, changes in opinions.items():
          s += f"{system}: {changes[idx]} "
        s += "\n"
    return s

  def _refresh_curr_match(self) -> None:
    self.curr_match = [self.db.retreive_profile(short_fname(prof.fullname))
                       for prof in self.curr_match]


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool, default_values_getter:Callable[[int],dict],
               sysnames:list[str]) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, default_values_getter)
    self.history_mgr = HistoryManager(img_dir)
    self.sysnames = sysnames

  def save_match(self, profiles:list[ProfileInfo], outcome:Outcome) -> None:
    self.history_mgr.save_match(
      time.time(),
      [short_fname(p.fullname) for p in profiles],
      outcome.tiers
    )

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

      self.meta_mgr.update(prof.fullname, new_ratings, len(profiles)-1, statistics.mean(proposed_stars))

  def update_meta(self, *args, **kwargs):
    self.meta_mgr.update_meta(*args, **kwargs)

  def give_awards(self, fullname, awards):
    self.meta_mgr.update(fullname, {'awards':awards})

  def get_search_results(self, query:str) -> list[ProfileInfo]:
    hits = self.meta_mgr.get_search_results(query)
    return [self._validate_and_convert_info(hits.iloc[i])
            for i in range(len(hits))]

  def get_leaderboard(self, sortpriority:list) -> list[ProfileInfo]:
    db = self.meta_mgr.get_db()
    db.sort_values(sortpriority, ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

  def get_tags_vocab(self) -> list[str]:
    return self.meta_mgr.get_tags_vocab()

  def retreive_profile(self, short_name:str) -> ProfileInfo:
    info = self.meta_mgr.get_file_info(short_name)
    return self._validate_and_convert_info(info)

  def retreive_rand_profiles(self, n:int) -> list[ProfileInfo]:
    sample = self.meta_mgr.get_rand_files_info(n)
    return [self._validate_and_convert_info(sample.iloc[i])
            for i in range(len(sample))]

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
      fullname=os.path.join(self.img_dir, short_name),
      stars=info['stars'],
      ratings={sname:Rating(info[sname+'_pts'], info[sname+'_rd'], info[sname+'_time'])
               for sname in self.sysnames},
      nmatches=int(info['nmatches']),
      awards=info['awards'].split(),
    )

  def on_exit(self):
    self.meta_mgr.on_exit()

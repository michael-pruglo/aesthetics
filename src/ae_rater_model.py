import logging
import os
import statistics
import time
import numpy as np
from typing import Callable

from ae_rater_types import *
from db_managers import MetadataManager, HistoryManager
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
    self.db = DBAccess(img_dir, refresh, default_values_getter)

  def get_curr_match(self) -> list[ProfileInfo]:
    return self.curr_match

  def generate_match(self, n:int=2) -> list[ProfileInfo]:
    self.curr_match = self.db.retreive_rand_profiles(n)
    return self.curr_match

  def get_leaderboard(self) -> list[ProfileInfo]:
    return self.db.get_leaderboard(sortpriority=[s.name()+"_pts" for s in self.rat_systems])

  def consume_result(self, outcome:Outcome) -> RatingOpinions:
    logging.info("consume_result outcome = %s", outcome.tiers)
    self.db.save_match(self.curr_match, outcome)

    opinions = {s.name(): s.process_match(self.curr_match, outcome)
                for s in self.rat_systems}
    logging.info("opinions:\n%s", self._pretty_opinions(opinions, outcome))
    self.db.apply_opinions(self.curr_match, opinions)

    self.curr_match = []
    return opinions

  def give_boost(self, short_name:str) -> None:
    profile = self.db.retreive_profile(short_name)
    self.db.save_boost(profile)
    logging.info("boost %s", profile)

    self.db.apply_opinions(
      [profile],
      {s.name(): [s.get_boost(profile)] for s in self.rat_systems},
    )

    self.curr_match = [self.db.retreive_profile(short_fname(prof.fullname))
                       for prof in self.curr_match]

  def on_exit(self):
    self.db.on_exit()

  def _pretty_opinions(self, opinions:RatingOpinions, outcome:Outcome) -> str:
    s = ""
    for letter in outcome.tiers:
      if letter.isspace():
        s += "\n\n"
      else:
        idx = ord(letter)-ord('a')
        s += f"\t{letter} {self.curr_match[idx]}  "
        for system, changes in opinions.items():
          s += f"{system}: {changes[idx]} "
        s += "\n"
    return s


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool, default_values_getter:Callable[[int],dict]) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, default_values_getter)
    self.history_mgr = HistoryManager(img_dir)

  def save_match(self, profiles:list[ProfileInfo], outcome:Outcome) -> None:
    self.history_mgr.save_match(
      time.time(),
      [short_fname(p.fullname) for p in profiles],
      outcome.tiers
    )

  def save_boost(self, profile:ProfileInfo) -> None:
    self.history_mgr.save_boost(time.time(), short_fname(profile.fullname))

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

  def get_leaderboard(self, sortpriority:list) -> list[ProfileInfo]:
    db = self.meta_mgr.get_db()
    db.sort_values(['stars']+sortpriority, ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

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

      # TODO: generalize
      'ELO_pts': np.int64,
      'ELO_rd': np.int64,
      'ELO_time': np.float64,
      'Glicko_pts': np.int64,
      'Glicko_rd': np.int64,
      'Glicko_time': np.float64,
    }
    assert all(col in info.index for col in expected_dtypes.keys()), str(info)
    assert 0 <= info['stars']
    for col,t in expected_dtypes.items():
      assert isinstance(info[col], t), f"{col} expected {t}  got {type(info[col])} {short_name}"

    return ProfileInfo(
      tags=info['tags'],
      fullname=os.path.join(self.img_dir, short_name),
      stars=info['stars'],
      ratings={
        'Glicko': Rating(info['Glicko_pts'], info['Glicko_rd'], info['Glicko_time']),
        'ELO': Rating(info['ELO_pts'], info['ELO_rd'], info['ELO_time']),
      },
      nmatches=int(info['nmatches']),
    )

  def on_exit(self):
    self.meta_mgr.on_exit()

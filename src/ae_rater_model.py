import logging
import os
import time
import numpy as np
from typing import Callable

from ae_rater_types import *
from db_managers import MetadataManager, HistoryManager
from rating_backends import RatingBackend, ELO
from helpers import short_fname


class RatingCompetition:
  def __init__(self, img_dir:str, refresh:bool):
    self.curr_match:list[ProfileInfo] = []
    self.rat_systems:list[RatingBackend] = [ELO(), ELO(1500, 100)]
    def default_values_getter(stars:int)->dict:
      return {s.name():s.stars_to_rating(stars) for s in self.rat_systems}
    self.db = DBAccess(img_dir, refresh, default_values_getter)

  def get_curr_match(self) -> list[ProfileInfo]:
    return self.curr_match

  def generate_match(self) -> list[ProfileInfo]:
    a = self.db.retreive_rand_profile()
    while True:
      b = self.db.retreive_rand_profile()
      if b.fullname != a.fullname:
        break
    self.curr_match = [a,b]
    return self.curr_match

  def get_leaderboard(self) -> list[ProfileInfo]:
    return self.db.get_leaderboard(sortpriority=[s.name() for s in self.rat_systems])

  def consume_result(self, outcome:Outcome) -> RatingOpinions:
    assert len(self.curr_match) == 2  # atm only accepts 1v1 matches
    logging.info("%s vs %s: %2d", *self.curr_match, outcome.value)
    self.db.save_match(self.curr_match, outcome)

    opinions = {s.name(): s.process_match(*self.curr_match, outcome)
                for s in self.rat_systems}
    logging.info("opinions: %s", opinions)
    self.db.apply_opinions(self.curr_match, opinions, is_match=True)

    self.curr_match = []
    return opinions

  def give_boost(self, short_name:str) -> None:
    profile = self.db.retreive_profile(short_name)
    self.db.save_boost(profile)
    logging.info("boost %s", profile)

    self.db.apply_opinions(
      [profile],
      {s.name(): [s.get_boost(profile)] for s in self.rat_systems},
      is_match=False,
    )

    self.curr_match = [self.db.retreive_profile(short_fname(prof.fullname))
                       for prof in self.curr_match]


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool, default_values_getter:Callable[[int],dict]) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, default_values_getter)
    self.history_mgr = HistoryManager(img_dir)

  def save_match(self, profiles:list[ProfileInfo], outcome:Outcome) -> None:
    self.history_mgr.save_match(
      int(time.time()),
      short_fname(profiles[0].fullname),
      short_fname(profiles[1].fullname),
      outcome.value
    )

  def save_boost(self, profile:ProfileInfo) -> None:
    self.history_mgr.save_boost(int(time.time()), short_fname(profile.fullname))

  def apply_opinions(self, profiles:list[ProfileInfo], opinions:RatingOpinions, is_match:bool) -> None:
    for i,prof in enumerate(profiles):
      new_ratings = {}
      proposed_stars = []
      for sysname,changes in opinions.items():
        proposed_stars.append(changes[i].new_stars)
        new_ratings[sysname] = changes[i].new_rating

      min_stars, max_stars = min(proposed_stars), max(proposed_stars)
      if min_stars == max_stars:
        consensus_stars = max_stars
      elif min_stars > prof.stars:
        consensus_stars = min_stars
      elif max_stars < prof.stars:
        consensus_stars = max_stars
      else:
        consensus_stars = None

      self.meta_mgr.update(prof.fullname, new_ratings, is_match, consensus_stars)

  def get_leaderboard(self, sortpriority:list) -> list[ProfileInfo]:
    db = self.meta_mgr.get_db()
    db.sort_values(['stars']+sortpriority, ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

  def retreive_profile(self, short_name:str) -> ProfileInfo:
    info = self.meta_mgr.get_file_info(short_name)
    return self._validate_and_convert_info(info)

  def retreive_rand_profile(self) -> ProfileInfo:
    info = self.meta_mgr.get_rand_file_info()
    return self._validate_and_convert_info(info)

  def _validate_and_convert_info(self, info) -> ProfileInfo:
    short_name = info.name

    expected_dtypes = {
      'tags': str,
      'stars': np.int64,
      'nmatches': np.int64,

      'Elo122': np.int64,  # TODO: generalize
      'Elo151': np.int64,
    }
    assert all(col in info.index for col in expected_dtypes.keys()), str(info)
    assert 0 <= info['stars'] <= 5
    for col,t in expected_dtypes.items():
      assert isinstance(info[col], t), f"{type(info[col])} {short_name}"

    return ProfileInfo(
      tags=info['tags'],
      fullname=os.path.join(self.img_dir, short_name),
      stars=int(info['stars']),
      ratings={n:int(info[n]) for n in ['Elo122', 'Elo151']},
      nmatches=int(info['nmatches']),
    )

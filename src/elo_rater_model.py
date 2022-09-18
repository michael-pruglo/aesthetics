import logging
import os
import time
import numpy as np

from elo_rater_types import RatChange, Outcome, ProfileInfo
from db_managers import MetadataManager, HistoryManager
from rating_backends import ELO
from helpers import short_fname


class EloCompetition:
  def __init__(self, img_dir:str, refresh:bool):
    self.db = DBAccess(img_dir, refresh)
    self.curr_match:list[ProfileInfo] = []

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
    return self.db.get_leaderboard()

  def consume_result(self, outcome:Outcome) -> list[RatChange]:
    assert len(self.curr_match) == 2
    elo_changes = ELO().process_match(*self.curr_match, outcome)

    logging.info("%s vs %s: %2d %s%s", *self.curr_match, outcome.value, *elo_changes)
    self.db.save_match(self.curr_match, outcome)
    self.db.update_rating(self.curr_match, elo_changes)

    self.curr_match = []
    return elo_changes

  def give_boost(self, profile:ProfileInfo) -> None:
    boost = 10
    logging.info("boost %d to %s", boost, profile)
    self.db.save_boost(profile, boost)
    self.db.update_rating([profile], [RatChange(profile.elo+boost, boost)])
    self.curr_match = [self.db.retreive_profile(short_fname(prof.fullname))
                       for prof in self.curr_match]


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, ELO().stars_to_rating)
    self.history_mgr = HistoryManager(img_dir)

  def save_match(self, profiles:list[ProfileInfo], outcome:Outcome) -> None:
    self.history_mgr.save_match(
      int(time.time()),
      short_fname(profiles[0].fullname),
      short_fname(profiles[1].fullname),
      outcome.value
    )

  def save_boost(self, profile:ProfileInfo, points:int) -> None:
    self.history_mgr.save_boost(int(time.time()), short_fname(profile.fullname), points)

  def update_rating(self, profiles:list[ProfileInfo], elo_changes:list[RatChange]) -> None:
    for profile,change in zip(profiles, elo_changes):
      self.meta_mgr.update_rating(
        profile.fullname,
        change.new_rating,
        ELO().rating_to_stars(change.new_rating)
      )

  def get_leaderboard(self) -> list[ProfileInfo]:
    db = self.meta_mgr.get_db()
    db.sort_values('elo', ascending=False, inplace=True)
    return [self._validate_and_convert_info(db.iloc[i]) for i in range(len(db))]

  def retreive_profile(self, short_name:str) -> ProfileInfo:
    try:
      info = self.meta_mgr.get_file_info(short_name)
      return self._validate_and_convert_info(info)
    except KeyError as e:
      print(e)
      return ProfileInfo("-", "err", -1, -1, -1)

  def retreive_rand_profile(self) -> ProfileInfo:
    info = self.meta_mgr.get_rand_file_info()
    return self._validate_and_convert_info(info)

  def _validate_and_convert_info(self, info) -> ProfileInfo:
    short_name = info.name

    expected_dtypes = {
      'tags': str,
      'stars': np.int64,
      'elo': np.int64,
      'nmatches': np.int64,
    }
    assert all(col in info.index for col in expected_dtypes.keys()), str(info)
    assert 0 <= info['stars'] <= 5
    for col,t in expected_dtypes.items():
      assert isinstance(info[col], t), f"{type(info[col])} {short_name}"

    return ProfileInfo(
      tags = info['tags'],
      fullname = os.path.join(self.img_dir, short_name),
      stars = int(info['stars']),
      elo = int(info['elo']),
      nmatches = int(info['nmatches']),
    )

import os
import numpy as np

from elo_rater_types import EloChange, Outcome, ProfileInfo
from metadata import MetadataManager


class ELOMath:
  @staticmethod
  def rat_to_elo(rat:int) -> int:
    return 1000 + 200*rat

  @staticmethod
  def elo_to_rat(elo:int) -> int:
    return np.clip((elo-1000)//200, 0, 5)

  @staticmethod
  def calc_change(l:ProfileInfo, r:ProfileInfo, outcome:Outcome) -> EloChange:
    delta = 15
    dright = delta * outcome.value
    return EloChange(
      new_elo_1 = l.elo-dright, delta_elo_1 = -dright,
      new_elo_2 = r.elo+dright, delta_elo_2 =  dright,
    )


class EloCompetition:
  def __init__(self, img_dir, refresh):
    self.db = DBAccess(img_dir, refresh)
    self.curr_match = None

  def get_next_match(self) -> tuple[ProfileInfo, ProfileInfo]:
    a = self.db.retreive_rand_profile()
    while True:
      b = self.db.retreive_rand_profile()
      if b.fullname != a.fullname:
        break
    self.curr_match = (a,b)
    return self.curr_match

  def consume_result(self, outcome:Outcome) -> EloChange:
    assert self.curr_match
    l, r = self.curr_match
    self.curr_match = None

    elo_change = ELOMath.calc_change(l, r, outcome)
    print(f"{l} vs {r}:  {elo_change}")
    self.db.update_elo(l, r, elo_change)

    return elo_change


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, ELOMath.rat_to_elo)

  def update_elo(self, l:ProfileInfo, r:ProfileInfo, elo_change:EloChange) -> None:
    self.meta_mgr.update_elo(l.short_name(), elo_change.new_elo_1, ELOMath.elo_to_rat(elo_change.new_elo_1))
    self.meta_mgr.update_elo(r.short_name(), elo_change.new_elo_2, ELOMath.elo_to_rat(elo_change.new_elo_2))

  def retreive_profile(self, short_name) -> ProfileInfo:
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
    assert all(info.index[:4] == ['tags', 'rating', 'elo', 'elo_matches'])
    assert isinstance(info['tags'], str)
    assert isinstance(info['rating'], np.int64)
    assert isinstance(info['elo'], np.int64)
    assert isinstance(info['elo_matches'], np.int64)
    short_name = info.name
    return ProfileInfo(
      tags = info['tags'],
      fullname = os.path.join(self.img_dir, short_name),
      rating = int(info['rating']),
      elo = int(info['elo']),
      elo_matches = int(info['elo_matches']),
    )

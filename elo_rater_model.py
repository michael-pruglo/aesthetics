from elo_rater_types import EloChange, Outcome, ProfileInfo
from metadata import MetadataManager

import os
from numpy import int64

def calc_elo_change(l:ProfileInfo, r:ProfileInfo, outcome:Outcome) -> EloChange:
  delta = 15
  dright = delta * outcome.value
  return EloChange(
    new_elo_1 = l.elo-dright, delta_elo_1 = -dright,
    new_elo_2 = r.elo+dright, delta_elo_2 =  dright,
  )

class EloCompetition:
  def __init__(self, img_dir, refresh):
    self.db = DBAccess(img_dir, refresh)
    self.curr_match:tuple[ProfileInfo, ProfileInfo] = ()

  def get_next_match(self) -> tuple[ProfileInfo, ProfileInfo]:
    a = self.db.retreive_rand_profile()
    while True:
      b = self.db.retreive_rand_profile()
      if b.fullname != a.fullname:
        break
    self.curr_match = (a,b)
    return self.curr_match

  def consume_result(self, outcome:Outcome) -> EloChange:
    l, r = self.curr_match
    self.curr_match = ()

    elo_change = calc_elo_change(l, r, outcome)
    print(f"{l} vs {r}:  {elo_change}")
    self.db.update_elo(l, r, elo_change)

    return elo_change

class DBAccess:
  def __init__(self, img_dir:str, refresh:bool) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh)
  
  def update_elo(self, l:ProfileInfo, r:ProfileInfo, elo_change:EloChange) -> None:
    self.meta_mgr.update_elo(l.short_name(), elo_change.new_elo_1)
    self.meta_mgr.update_elo(r.short_name(), elo_change.new_elo_2)

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
    assert type(info['tags']) == str
    assert type(info['rating']) == int64
    assert type(info['elo']) == int64
    assert type(info['elo_matches']) == int64
    short_name = info.name
    return ProfileInfo(
      tags = info['tags'],
      fullname = os.path.join(self.img_dir, short_name),
      rating = info['rating'],
      elo = info['elo'],
      elo_matches = info['elo_matches'],
    )

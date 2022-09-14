import logging
import os
import numpy as np

from elo_rater_types import EloChange, Outcome, ProfileInfo
from metadata import MetadataManager
from helpers import short_fname


class ELOMath:
  INITIAL_ELO = 1200
  STD = 200

  @staticmethod
  def rat_to_elo(rat:int) -> int:
    return ELOMath.INITIAL_ELO + ELOMath.STD*rat

  @staticmethod
  def elo_to_rat(elo:int) -> int:
    return np.clip((elo-ELOMath.INITIAL_ELO)//ELOMath.STD, 0, 5)

  @staticmethod
  def calc_change(l:ProfileInfo, r:ProfileInfo, outcome:Outcome) -> EloChange:
    ql = 10**(l.elo/400)
    qr = 10**(r.elo/400)
    er = qr/(ql+qr)
    sr = np.interp(outcome.value, [-1,1], [0,1])
    delta = sr-er
    dl = round(ELOMath.get_k(l) * -delta)
    dr = round(ELOMath.get_k(r) *  delta)
    return EloChange(
      new_elo_1 = l.elo+dl, delta_elo_1 = dl,
      new_elo_2 = r.elo+dr, delta_elo_2 = dr,
    )

  @staticmethod
  def get_k(p:ProfileInfo) -> float:
    if p.elo_matches<30 and p.elo<2300:
      return 40
    if p.elo_matches>30 and p.elo>2400:
      return 10
    return 20

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
    logging.info("%s vs %s:  %s", l, r, elo_change)
    self.db.update_elo(l, r, elo_change)

    return elo_change


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, ELOMath.rat_to_elo)

  def update_elo(self, l:ProfileInfo, r:ProfileInfo, elo_change:EloChange) -> None:
    self.meta_mgr.update_elo(short_fname(l.fullname), elo_change.new_elo_1, ELOMath.elo_to_rat(elo_change.new_elo_1))
    self.meta_mgr.update_elo(short_fname(r.fullname), elo_change.new_elo_2, ELOMath.elo_to_rat(elo_change.new_elo_2))

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

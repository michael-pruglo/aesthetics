import logging
import os
import time
import numpy as np

from elo_rater_types import EloChange, Outcome, ProfileInfo
from db_managers import MetadataManager, HistoryManager
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
  def calc_changes(l:ProfileInfo, r:ProfileInfo, outcome:Outcome) -> list[EloChange]:
    ql = 10**(l.elo/400)
    qr = 10**(r.elo/400)
    er = qr/(ql+qr)
    sr = np.interp(outcome.value, [-1,1], [0,1])
    delta = sr-er
    dl = round(ELOMath.get_k(l) * -delta)
    dr = round(ELOMath.get_k(r) *  delta)
    return [EloChange(l.elo+dl, dl),EloChange(r.elo+dr, dr)]

  @staticmethod
  def get_k(p:ProfileInfo) -> float:
    if p.elo_matches<30 and p.elo<2300:
      return 40
    if p.elo_matches>30 and p.elo>2400:
      return 10
    return 20

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

  def consume_result(self, outcome:Outcome) -> list[EloChange]:
    assert len(self.curr_match) == 2
    elo_changes = ELOMath.calc_changes(*self.curr_match, outcome)

    logging.info("%s vs %s: %2d %s%s", *self.curr_match, outcome.value, *elo_changes)
    self.db.save_match(self.curr_match, outcome)
    self.db.update_elo(self.curr_match, elo_changes)

    self.curr_match = []
    return elo_changes


class DBAccess:
  def __init__(self, img_dir:str, refresh:bool) -> None:
    self.img_dir = img_dir
    self.meta_mgr = MetadataManager(img_dir, refresh, ELOMath.rat_to_elo)
    self.history_mgr = HistoryManager(img_dir)

  def save_match(self, profiles:list[ProfileInfo], outcome:Outcome) -> None:
    self.history_mgr.save_match(
      int(time.time()),
      short_fname(profiles[0].fullname),
      short_fname(profiles[1].fullname),
      outcome.value
    )

  def update_elo(self, profiles:list[ProfileInfo], elo_changes:list[EloChange]) -> None:
    for profile,change in zip(profiles, elo_changes):
      self.meta_mgr.update_elo(
        short_fname(profile.fullname),
        change.new_elo,
        ELOMath.elo_to_rat(change.new_elo)
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
    assert all(info.index[:4] == ['tags', 'rating', 'elo', 'elo_matches']), str(info)
    assert isinstance(info['tags'],        str),      f"{type(info['tags'])       }  {short_name}"
    assert isinstance(info['rating'],      np.int64), f"{type(info['rating'])     }  {short_name}"
    assert isinstance(info['elo'],         np.int64), f"{type(info['elo'])        }  {short_name}"
    assert isinstance(info['elo_matches'], np.int64), f"{type(info['elo_matches'])}  {short_name}"
    assert 0 <= info['rating'] <= 5
    return ProfileInfo(
      tags = info['tags'],
      fullname = os.path.join(self.img_dir, short_name),
      rating = int(info['rating']),
      elo = int(info['elo']),
      elo_matches = int(info['elo_matches']),
    )

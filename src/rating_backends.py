from abc import ABC, abstractmethod
import numpy as np
from elo_rater_types import ProfileInfo, Outcome, EloChange


class RatingBackend(ABC):
  @abstractmethod
  def rating_to_stars(self, rat:int) -> int:
    pass

  @abstractmethod
  def stars_to_rating(self, stars:int) -> int:
    pass

  @abstractmethod
  def process_match(self, l:ProfileInfo, r:ProfileInfo,
                    outcome:Outcome) -> list[EloChange]:
    pass

class ELO(RatingBackend):
  def __init__(self, base_rating=1200, std=200):
    super().__init__()
    self.BASE_RATING = base_rating # new player with 0 stars
    self.STD = std

  def stars_to_rating(self, stars:int) -> int:
    return self.BASE_RATING + self.STD*stars

  def rating_to_stars(self, rat:int) -> int:
    return np.clip((rat-self.BASE_RATING)//self.STD, 0, 5)

  def process_match(self, l:ProfileInfo, r:ProfileInfo,
                    outcome:Outcome) -> list[EloChange]:
    ql = 10**(l.elo/(self.STD*2))
    qr = 10**(r.elo/(self.STD*2))
    er = qr/(ql+qr)
    sr = np.interp(outcome.value, [-1,1], [0,1])
    delta = sr-er
    dl = round(self.get_k(l) * -delta)
    dr = round(self.get_k(r) *  delta)
    return (EloChange(l.elo+dl,dl), EloChange(r.elo+dr,dr))

  def get_k(self, p:ProfileInfo) -> float:
    if p.nmatches<30 and p.elo<2300:
      return 40
    if p.nmatches>30 and p.elo>2400:
      return 10
    return 20

class Glicko(RatingBackend):
  pass

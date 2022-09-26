from abc import ABC, abstractmethod
import math
import time
import numpy as np
from ae_rater_types import *


class RatingBackend(ABC):
  @abstractmethod
  def stars_to_rating(self, stars:float) -> Rating:
    pass

  @abstractmethod
  def rating_to_stars(self, rat:Rating) -> float:
    pass

  @abstractmethod
  def process_match(self, l:ProfileInfo, r:ProfileInfo,
                    outcome:Outcome) -> list[RatChange]:
    pass

  def name(self) -> RatSystemName:
    return type(self).__name__

  def get_default_values(self, stars:float) -> dict:
    def_rat = self.stars_to_rating(stars)
    return {
      self.name()+"_pts": def_rat.points,
      self.name()+"_rd": def_rat.rd,
      self.name()+"_time": def_rat.timestamp,
    }

  def get_boost(self, profile:ProfileInfo) -> RatChange:
    delta = 10
    rating = profile.ratings[self.name()]
    new_pts = rating.points + delta
    new_rat = Rating(new_pts, rating.rd)
    return RatChange(new_rat, delta, self.rating_to_stars(new_rat))


class ELO(RatingBackend):
  def __init__(self, base_rating=1200, std=200):
    super().__init__()
    self.BASE_RATING = base_rating  # new player with 0 stars
    self.STD = std

  def stars_to_rating(self, stars):
    return Rating(int(self.BASE_RATING + self.STD*stars))

  def rating_to_stars(self, rat):
    return max((rat.points-self.BASE_RATING)/self.STD, 0.0)

  def process_match(self, l, r, outcome):
    lpts = l.ratings[self.name()].points
    rpts = r.ratings[self.name()].points
    ql = 10**(lpts/(self.STD*2))
    qr = 10**(rpts/(self.STD*2))
    er = qr/(ql+qr)
    sr = np.interp(outcome.value, [-1,1], [0,1])
    delta = sr-er
    dl = round(self._get_k(l) * -delta)
    dr = round(self._get_k(r) *  delta)
    new_lrat = Rating(lpts+dl)
    new_rrat = Rating(rpts+dr)
    return [
      RatChange(new_lrat, dl, self.rating_to_stars(new_lrat)),
      RatChange(new_rrat, dr, self.rating_to_stars(new_rrat)),
    ]

  def _get_k(self, p):
    ppts = p.ratings[self.name()].points
    if p.nmatches<30 and ppts<2300:
      return 40
    if p.nmatches>30 and ppts>2400:
      return 10
    return 20


class Glicko(RatingBackend):
  def __init__(self):
    super().__init__()
    self.BASE_POINTS = 1500
    self.MIN_RD = 25
    self.MAX_RD = 350

  def stars_to_rating(self, stars):
    return Rating(int(self.BASE_POINTS+self.MAX_RD*stars), self.MAX_RD, time.time())

  def rating_to_stars(self, rat):
    return max((rat.points-self.BASE_POINTS)/self.MAX_RD, 0.0)

  # http://glicko.net/glicko/glicko.pdf
  def process_match(self, l, r, outcome):
    lrat = l.ratings[self.name()]
    rrat = r.ratings[self.name()]
    assert self.MIN_RD <= lrat.rd <= self.MAX_RD
    assert self.MIN_RD <= rrat.rd <= self.MAX_RD
    lrat.rd = self._update_rd(lrat)
    rrat.rd = self._update_rd(rrat)
    converted_outcome = {
      Outcome.WIN_LEFT: 1,
      Outcome.DRAW: 1/2,
      Outcome.WIN_RIGHT: 0,
    }[outcome]
    new_lrat = self._calc_new_rat(lrat, rrat, converted_outcome)
    new_rrat = self._calc_new_rat(rrat, lrat, 1-converted_outcome)
    return [
      RatChange(new_lrat, new_lrat.points-lrat.points, self.rating_to_stars(new_lrat)),
      RatChange(new_rrat, new_rrat.points-rrat.points, self.rating_to_stars(new_rrat)),
    ]

  def _update_rd(self, rating:Rating) -> int:
    days_since_last_match = (time.time()-rating.timestamp)/86400
    c = days_since_last_match
    new_rd = round(math.sqrt(rating.rd**2 + c**2))
    return min(new_rd, self.MAX_RD)

  def _calc_new_rat(self, main:Rating, opponent:Rating, s:float) -> Rating:
    q = math.log(10)/400
    # almost a straight line, g close to 1 at rd=0 and slowly lowers to .67 at rd=350
    g = 1/math.sqrt(1 + 3 * q**2 * opponent.rd**2 / math.pi**2)
    # expected outcome, closer to extremes [0,1] when rd is low
    e = 1/(1 + 10**(-g*(main.points-opponent.points)/400))
    # huuuuuge number, 200k even at rd=0, and grows as 4th power
    d2 = 1/(q**2 * g**2 * e*(1-e))
    new_pts = main.points + q/(1/main.rd**2+1/d2) * g*(s-e)

    new_rd = math.sqrt(1/(1/main.rd**2 + 1/d2))

    return Rating(
      round(new_pts),
      max(self.MIN_RD, round(new_rd)),
      time.time(),
    )

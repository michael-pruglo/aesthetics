from abc import ABC, abstractmethod
import math
import time
from ae_rater_types import *

import logging

class RatingBackend(ABC):
  @abstractmethod
  def stars_to_rating(self, stars:float) -> Rating:
    pass

  @abstractmethod
  def rating_to_stars(self, rat:Rating) -> float:
    pass

  def process_match(self, match:MatchInfo) -> list[RatChange]:
    # print("\n ---- ")
    # print("initial: ", [p.ratings[self.name()] for p in match.profiles])

    boosts = []
    for i,p in enumerate(match.profiles):
      mult = match.outcome.boosts[i] if i in match.outcome.boosts else 0
      boost = self.get_boost(p, mult).delta_rating
      boosts.append(boost)
      match.profiles[i].ratings[self.name()].points += boost

    # print("after:   ", [p.ratings[self.name()] for p in match.profiles])

    changes = self._process_match_strategy(match)
    ret = [RatChange(ch.new_rating, ch.delta_rating+boost, ch.new_stars)
            for ch,boost in zip(changes, boosts)]

    # print("boosts:  ", boosts)
    # print("changes: ", changes)
    # print("ret:     ", ret)
    # print(" ---- \n")

    return ret

  @abstractmethod
  def _process_match_strategy(self, match:MatchInfo) -> list[RatChange]:
    pass

  def name(self) -> RatSystemName:
    return type(self).__name__

  def get_boost(self, profile:ProfileInfo, mult:int=1) -> RatChange:
    delta = 10 * mult
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

  def _process_match_strategy(self, match):
    logging.info("exec")
    changes = [0] * len(match.profiles)
    for curr, matches in match.outcome.as_dict().items():
      for opponent, sr in matches:
        changes[curr] += self._process_pair(match.profiles[curr], match.profiles[opponent], sr)[0].delta_rating
    ret = []
    for i, prof in enumerate(match.profiles):
      newrat = Rating(prof.ratings[self.name()].points + changes[i])
      ret.append(RatChange(newrat, changes[i], self.rating_to_stars(newrat)))
    return ret

  def _process_pair(self, l, r, sr):
    lpts = l.ratings[self.name()].points
    rpts = r.ratings[self.name()].points
    ql = 10**(lpts/(self.STD*2))
    qr = 10**(rpts/(self.STD*2))
    er = ql/(ql+qr)
    delta = sr-er
    dl = round(self._get_k(l) * delta)
    dr = round(self._get_k(r) *-delta)
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
  def _process_match_strategy(self, match):
    logging.info("exec")
    for i in match.outcome.as_dict().keys():
      currat = match.profiles[i].ratings[self.name()]
      assert self.MIN_RD <= currat.rd <= self.MAX_RD
      currat.rd = self._update_rd(match.timestamp, currat)
      assert self.MIN_RD <= currat.rd <= self.MAX_RD

    ret = []
    for i, matches in sorted(match.outcome.as_dict().items()):
      currat = match.profiles[i].ratings[self.name()]
      newrat = self._calc_new_rat(currat, [match.profiles[m[0]].ratings[self.name()] for m in matches], [m[1] for m in matches])
      ret.append(RatChange(newrat, newrat.points-currat.points, self.rating_to_stars(newrat)))
    return ret

  def _update_rd(self, match_timestamp, rating:Rating) -> int:
    days_since_last_match = (match_timestamp-rating.timestamp)/86400
    assert days_since_last_match >= 0
    c = days_since_last_match
    new_rd = round(math.sqrt(rating.rd**2 + c**2))
    return min(new_rd, self.MAX_RD)

  def _calc_new_rat(self, main:Rating, opponents:list[Rating], results:list[float]) -> Rating:
    q = math.log(10)/400
    # almost a straight line, g close to 1 at rd=0 and slowly lowers to .67 at rd=350
    g = lambda rdj: 1/math.sqrt(1 + 3 * q**2 * rdj**2 / math.pi**2)
    # expected outcome, closer to extremes [0,1] when rd is low
    e = lambda rj,rdj: 1/(1 + 10**(-g(rdj)*(main.points-rj)/400))
    # huuuuuge number, 200k even at rd=0, and grows as 4th power
    d2 = 1/(q**2 * sum([g(p.rd)**2 * e(p.points,p.rd)*(1-e(p.points,p.rd))
                        for p in opponents]))
    new_pts = main.points + q/(1/main.rd**2+1/d2) * sum([g(p.rd)*(s-e(p.points,p.rd)) for p,s in zip(opponents,results)])
    new_rd = math.sqrt(1/(1/main.rd**2 + 1/d2))

    return Rating(
      round(new_pts),
      max(self.MIN_RD, round(new_rd)),
      time.time(),
    )

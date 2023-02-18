import string
import time
from enum import Enum, auto
from typing import Iterable
from dataclasses import dataclass, field
from functools import total_ordering
from numpy import interp
from pandas import Series

from helpers import truncate, short_fname
from metadata import ManualMetadata


@dataclass
@total_ordering
class Rating:
  points: int
  rd: int = 0
  timestamp: float = field(default_factory=time.time)

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      raise NotImplementedError
    return self.points == other.points and self.rd == other.rd

  def __lt__(self, other):
    if not isinstance(other, type(self)):
      raise NotImplementedError
    return (
      self.points < other.points
      or (self.points == other.points and self.rd > other.rd)
    )

  def __repr__(self):
    return f"{self.points}`{self.rd}`"


@dataclass
class ProfileInfo:
  fullname : str
  tags : str = ""
  stars : float = 0
  ratings : dict[str,Rating] = field(default_factory=dict)
  nmatches : int = 0
  awards: str = ""

  def stronger_than(self, other):
    if not isinstance(other, self.__class__):
      raise TypeError(f"cannot compare to {type(other)}")
    if not set(self.ratings.keys()) == set(other.ratings.keys()):
      raise ValueError(f"cannot compare profiles with different sets of ratings")
    return (
      self.stars >= other.stars
      and all(self.ratings[s] >= other.ratings[s] for s in self.ratings.keys())
      and any(self.ratings[s] >  other.ratings[s] for s in self.ratings.keys())
    )

  def __str__(self):
    BG_GRAY     = "\033[48;5;236m"
    FG_WHITE    = "\033[38;5;231m"
    FG_YELLOW   = "\033[38;5;214m"
    FG_ELO      = "\033[38;5;{}m".format([0,26,2,228,208,9][min(5, int(self.stars))])
    FG_MATCHES  = "\033[38;5;{}m".format(int(interp(self.nmatches, [0,100], [232,255])))
    COLOR_RESET = "\033[0;0m"
    return ''.join([
      BG_GRAY,
      FG_WHITE,   f"{truncate(short_fname(self.fullname), 15):<15} ",
      FG_YELLOW,  f"{f'★{self.stars:.2f}':>5} ",
      FG_ELO,     f"{self.ratings} ",
      FG_MATCHES, f"{f'({self.nmatches})':<5} ",
      FG_WHITE,   f"aw:{len(self.awards.split())}",
      COLOR_RESET
    ])


@dataclass
class RatChange:
  new_rating : Rating
  delta_rating : int
  new_stars : float

  def __repr__(self):
      BG_GRAY     = "\033[48;5;238m"
      FG_WHITE    = "\033[38;5;231m"
      FG_YELLOW   = "\033[38;5;214m"
      FG_RED      = "\033[38;5;196m"
      FG_GRAY     = "\033[38;5;248m"
      FG_GREEN    = "\033[38;5;46m"
      COLOR_RESET = "\033[0;0m"
      if   self.delta_rating<0: delta_color = FG_RED
      elif self.delta_rating>0: delta_color = FG_GREEN
      else:                  delta_color = FG_GRAY
      return ''.join([
        BG_GRAY,
        FG_WHITE,    f" {str(self.new_rating):>6}",
        FG_YELLOW,   f"{f'★{self.new_stars:.2f}':>5} ",
        delta_color, f"{f'[{self.delta_rating:+}]':>5} ",
        COLOR_RESET
      ])


RatSystemName = str
RatingOpinions = dict[RatSystemName, list[RatChange]]
DiagnosticInfo = Series


class Outcome:
  def __init__(self, s:str):
    if not self.is_valid(s):
      raise ValueError(f"cannot parse outcome from '{s}'")

    self.boosts = self._parse_boosts(s)
    self.tiers = s.translate({ord(i):None for i in "+-"})

  @staticmethod
  def idx_to_let(idx:int) -> str:
    return chr(ord('a') + idx)

  @staticmethod
  def let_to_idx(letter:str) -> int:
    return ord(letter) - ord('a')

  @staticmethod
  def is_valid(outcome:str, n:int=None, intermediate=False) -> bool:
    if outcome == "":
      return intermediate

    # validate +-
    for i in range(len(outcome)):
      if outcome[i] in "+-":
        if i==0:
          return False
        if not (outcome[i-1].isalpha() or outcome[i-1] in "+-"):
          return False
    s = outcome.translate({ord(i):None for i in "+-"})

    # validate other symbols
    s = ''.join(sorted(s.lower())).strip()
    biggest_idx = Outcome.let_to_idx(s[-1])
    if n is None:
      n = biggest_idx+1
    if not intermediate:
      return len(s)==n and s==string.ascii_lowercase[:n]
    else:
      return s.isalpha() and len(s)<=n and biggest_idx<n and len(set(s))==len(s)

  @staticmethod
  def predict_tiers_intermediate(outcome:str, n:int) -> tuple[dict,int]:
    if outcome == "":
      return {}, n

    assert Outcome.is_valid(outcome, n, intermediate=True)

    s = outcome.translate({ord(i):None for i in "+-"})

    class Mode(Enum):
      LEADERS = auto()
      MID = auto()
      LOSERS = auto()
    mode = Mode.LEADERS
    if outcome[0].isspace():
      mode = Mode.MID if outcome[-1].isspace() else Mode.LOSERS

    pred_tiers = {}
    tiers = s.split()
    letters_remaining = n
    for i, tier in enumerate(tiers):
      for letter in tier:
        pred_tiers[Outcome.let_to_idx(letter)] = i
        letters_remaining -= 1

    pred_max_tiers = len(tiers) + letters_remaining

    if mode != Mode.LEADERS:
      for key in pred_tiers:
        coef = 1 if mode == Mode.LOSERS else 2
        pred_tiers[key] += (pred_max_tiers-len(tiers))//coef

    return pred_tiers, pred_max_tiers

  def get_boosts(self) -> dict[int,int]:
    """parse + and -, return dict idx->boost_multiplier"""
    return self.boosts

  def as_dict(self) -> dict[int,list[tuple[int,float]]]:
    """return dict of results idx->list of matches (opponent_idx,points)"""
    matches = {}
    li_tiers = self.tiers.split()
    for i, tier in enumerate(li_tiers):
      for curr in tier:
        currmatches = []
        for loss in ''.join(li_tiers[:i]):
          currmatches.append((self.let_to_idx(loss), 0.0))
        for draw in tier:
          if draw!=curr:
            currmatches.append((self.let_to_idx(draw), 0.5))
        for win in ''.join(li_tiers[i+1:]):
          currmatches.append((self.let_to_idx(win), 1.0))
        matches[self.let_to_idx(curr)] = currmatches
    return matches

  def _parse_boosts(self, s):
    boosts = {}
    mult = 0
    curr_let = ''
    for c in s+' ':  # to seamlessly handle +- at end
      if c == '+':
        mult += 1
      elif c == '-':
        mult -= 1
      else:
        if mult:
          assert curr_let
          boosts[self.let_to_idx(curr_let)] = mult
          mult = 0
        if not c.isspace():
          curr_let = c
    return boosts

  def __eq__(self, other):
    if not isinstance(other, type(self)):
      return False
    return self.tiers == other.tiers

  def __hash__(self) -> int:
    return hash(self.tiers)


@dataclass
class MatchInfo:
  profiles: list[ProfileInfo]
  outcome: Outcome
  timestamp: float = field(default_factory=time.time)


class UserListener:
  def start_next_match(self) -> None:
    raise NotImplementedError()

  def consume_result(self, outcome:Outcome) -> None:
    raise NotImplementedError()

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    raise NotImplementedError()

  def suggest_tags(self, fullname:str) -> list:
    raise NotImplementedError()

  def search_for(self, query:str) -> None:
    raise NotImplementedError()


class AppMode(Enum):
  MATCH = auto()
  SEARCH = auto()

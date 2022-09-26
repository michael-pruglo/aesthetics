import time
from dataclasses import dataclass, field
from enum import Enum
from functools import total_ordering
from numpy import interp

from helpers import truncate, short_fname


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

  def __str__(self):
    return f"{self.points}`{self.rd}`"


@dataclass
class ProfileInfo:
  tags : str
  fullname : str
  stars : float
  ratings : dict[str,Rating]
  nmatches : int

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
      FG_MATCHES, f"{f'({self.nmatches})':<5}",
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


class Outcome(Enum):
  WIN_LEFT = -1
  DRAW = 0
  WIN_RIGHT = 1

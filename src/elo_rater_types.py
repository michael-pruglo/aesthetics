from dataclasses import dataclass
from enum import Enum
from numpy import interp

from helpers import truncate, short_fname


@dataclass
class ProfileInfo:
  tags : str
  fullname : str
  stars : int
  elo : int
  nmatches : int

  def __str__(self):
    BG_GRAY     = "\033[48;5;236m"
    FG_WHITE    = "\033[38;5;231m"
    FG_YELLOW   = "\033[38;5;214m"
    FG_ELO      = "\033[38;5;{}m".format([0,26,2,228,208,9][self.stars])
    FG_MATCHES  = "\033[38;5;{}m".format(int(interp(self.nmatches, [0,100], [232,255])))
    COLOR_RESET = "\033[0;0m"
    return ''.join([
      BG_GRAY,
      FG_WHITE,   f"{truncate(short_fname(self.fullname), 15):<15} ",
      FG_YELLOW,  f"{'★' * self.stars:>5} ",
      FG_ELO,     f"{self.elo:>4} ",
      FG_MATCHES, f"{f'({self.nmatches})':<5}",
      COLOR_RESET
    ])


@dataclass
class RatChange:
  new_rating : int
  delta_rating : int

  def __str__(self):
      BG_GRAY     = "\033[48;5;238m"
      FG_WHITE    = "\033[38;5;231m"
      FG_RED      = "\033[38;5;196m"
      FG_GRAY     = "\033[38;5;248m"
      FG_GREEN    = "\033[38;5;46m"
      COLOR_RESET = "\033[0;0m"
      if   self.delta_rating<0: delta_color = FG_RED
      elif self.delta_rating>0: delta_color = FG_GREEN
      else:                  delta_color = FG_GRAY
      return ''.join([
        BG_GRAY,
        FG_WHITE,    f" {self.new_rating:>4}",
        delta_color, f"{f'[{self.delta_rating:+}]':>5} ",
        COLOR_RESET
      ])


class Outcome(Enum):
  WIN_LEFT = -1
  DRAW = 0
  WIN_RIGHT = 1

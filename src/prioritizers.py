from functools import partial
from enum import Enum, auto
import pandas as pd
from typing import Callable
import statistics


def match_coef(maxmat, row):
  return max(0.0, (maxmat-row['nmatches'])/maxmat)

def star_coef(p, row):
  MAXSTARS = 6.5
  return min(1.0, (row['stars']/MAXSTARS)**p)


class PrioritizerType(Enum):
  DEFAULT = auto()
  FRESH = auto()
  TOP = auto()

def make_prioritizer(type:PrioritizerType = PrioritizerType.DEFAULT):
  if type == PrioritizerType.FRESH:
    return Prioritizer([
      partial(match_coef, 20),
    ])

  if type == PrioritizerType.TOP:
    return Prioritizer([
      partial(star_coef, 2),
    ])

  return Prioritizer([
    partial(match_coef, 40),
    partial(star_coef, 1.5),
  ])


class Prioritizer:
  def __init__(self, ops:list[Callable[[pd.Series], float]]):
    self.ops = ops

  def calc(self, row:pd.Series) -> pd.Series:
    row.loc['priority'] = statistics.mean([op(row) for op in self.ops]) if self.ops else 0
    return row

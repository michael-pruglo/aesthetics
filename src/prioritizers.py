from functools import partial
from enum import Enum
import pandas as pd
from typing import Callable
import statistics


def match_coef(maxmat, row):
  return max(0.0, (maxmat-row['nmatches'])/maxmat)

def star_coef(p, row):
  MAXSTARS = 6.5
  return min(1.0, (row['stars']/MAXSTARS)**p)

def keyword_coef(word, row):
  coef = 0
  cols = ['tags', 'awards']
  for col in cols:
    coef += 1/len(cols) * float(word in row[col])
  assert 0 <= coef <= 1
  return coef


class PrioritizerType(Enum):
  DEFAULT = "default"
  FRESH = "fresh"
  TOP = "top"
  KEYWORD = "keyword"
  def __str__(self):
    return self.value

def make_prioritizer(type:PrioritizerType):
  if type == PrioritizerType.FRESH:
    return Prioritizer([
      partial(match_coef, 50),
    ])

  if type == PrioritizerType.TOP:
    return Prioritizer([
      partial(star_coef, 4),
    ])

  if type == PrioritizerType.KEYWORD:
    return Prioritizer([
      partial(keyword_coef, "face"),
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

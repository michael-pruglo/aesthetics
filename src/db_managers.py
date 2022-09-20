import logging
import os
import pandas as pd
from typing import Callable

from metadata import get_metadata, write_metadata
from helpers import short_fname


def _db_row(fname):
  tags, stars = get_metadata(fname)
  assert tags, f"media without tags not allowed: {short_fname(fname)}"
  return {
    'name': short_fname(fname),
    'tags': ' '.join(sorted(tags)).lower(),
    'stars': int(stars),
  }


def _default_init(row, default_values_getter):
  assert 0 <= row['stars'] <= 5
  if row.isna()['nmatches']:
    row['nmatches'] = 0
  for column, value in default_values_getter(row['stars']).items():
    row[column] = value
  return row


class MetadataManager:
  def __init__(self, img_dir:str, refresh:bool=False, defaults_getter:Callable[[int], dict]=None):
    self.db_fname = os.path.join(img_dir, 'metadata_db.csv')
    metadata_dtypes = {
      'name': str,
      'tags': str,
      'stars': int,
      'nmatches': int,
    }
    if os.path.exists(self.db_fname):
      logging.info("metadata csv exists, read")
      self.df = pd.read_csv(self.db_fname, keep_default_na=False, dtype=metadata_dtypes)
    else:
      logging.info("metadata csv does not exist, create")
      self.df = pd.DataFrame(columns=metadata_dtypes.keys())
    self.df.set_index('name', inplace=True)

    if refresh or not os.path.exists(self.db_fname):
      logging.info("refreshing metadata db...")
      def is_media(fname):
        return fname.find('.')>0 and not fname.endswith('.csv')
      fnames = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if is_media(f)]
      fresh_tagrat = pd.DataFrame(_db_row(fname) for fname in fnames).set_index('name')
      self.df = self.df.combine(fresh_tagrat, lambda old,new: new.fillna(old), overwrite=False)[self.df.columns]
      self.df = self.df.apply(_default_init, axis=1, args=(defaults_getter,))
      self.df.sort_values('stars', ascending=False, inplace=True)
      self._commit()

  def get_db(self, min_tag_freq:int=0) -> pd.DataFrame:
    if min_tag_freq:
      freq_tags = self._get_frequent_tags(min_tag_freq)
      logging.info("frequency of tags (threshold %d):\n%s", freq_tags, min_tag_freq)
      dfc = self.df.copy()
      def remove_infrequent(s):
        return ' '.join([tag for tag in s.split(' ') if tag in freq_tags])
      dfc['tags'] = dfc['tags'].apply(remove_infrequent)
      return dfc

    return self.df

  def get_file_info(self, short_name:str) -> pd.Series:
    if short_name not in self.df.index:
      raise KeyError(f"{short_name} not in database")
    return self.df.loc[short_name]

  def get_rand_file_info(self) -> pd.Series:
    return self.df.sample().iloc[0]

  def update(self, fullname:str, values:dict, consensus_stars:int=None) -> None:
    short_name = short_fname(fullname)
    if short_name not in self.df.index:
      raise KeyError(f"{short_name} not in database")

    for column,value in values.items():
      self.df.loc[short_name, column] = value  # TODO: prettify with pandas

    if consensus_stars:
      prev_stars = self.df.loc[short_name, 'stars']
      if prev_stars != consensus_stars:
        assert 0 <= consensus_stars <= 5
        self.df.loc[short_name, 'stars'] = consensus_stars
        write_metadata(fullname, rating=consensus_stars)
        logging.info("file %s updated stars on disk: %s -> %s",
                     short_name, '★'*prev_stars, '★'*consensus_stars)

    self.df.loc[short_name, 'nmatches'] += 1

    logging.debug("updated db: %s", self.df.loc[short_name])
    self._commit()

  def _get_frequent_tags(self, min_tag_freq):
    lists = self.df['tags'].str.split(' ')
    tag_freq = pd.concat([pd.Series(l) for l in lists], ignore_index=True).value_counts()
    return tag_freq[tag_freq>=min_tag_freq]

  def _commit(self):
    self.df.to_csv(self.db_fname)


class HistoryManager:
  def __init__(self, img_dir:str):
    self.matches_fname = os.path.join(img_dir, 'match_history.csv')
    match_history_dtypes = {
      "timestamp": int,
      "name1": str,
      "name2": str,
      "outcome": int,
    }
    if os.path.exists(self.matches_fname):
      logging.info("match_history csv exists, read")
      self.matches_df = pd.read_csv(self.matches_fname, dtype=match_history_dtypes)
    else:
      logging.info("match_history csv does not exist, create")
      self.matches_df = pd.DataFrame(columns=match_history_dtypes.keys())

    self.boosts_fname = os.path.join(img_dir, 'boosts_history.csv')
    boosts_dtypes = {
      "timestamp": int,
      "name": str,
    }
    if os.path.exists(self.boosts_fname):
      logging.info("boosts csv exists, read")
      self.boosts_df = pd.read_csv(self.boosts_fname, dtype=boosts_dtypes)
    else:
      logging.info("boosts csv does not exist, create")
      self.boosts_df = pd.DataFrame(columns=boosts_dtypes.keys())

  def save_match(self, timestamp:int, name1:str, name2:str, outcome:int) -> None:
    self.matches_df.loc[len(self.matches_df)] = [timestamp, name1, name2, outcome]
    self.matches_df.to_csv(self.matches_fname, index=False)

  def save_boost(self, timestamp:int, name:str) -> None:
    self.boosts_df.loc[len(self.boosts_df)] = [timestamp, name]
    self.boosts_df.to_csv(self.boosts_fname, index=False)

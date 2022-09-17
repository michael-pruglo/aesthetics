import logging
import os
import pandas as pd
from typing import Callable

from metadata import get_metadata
from helpers import short_fname


def _db_row(fname):
  tags, rating = get_metadata(fname)
  return {
    'name': short_fname(fname),
    'tags': ' '.join(sorted(tags)).lower(),
    'rating': int(rating),
  }

def _default_elo(row, default_elo:Callable[[int], int]):
  is_nan = row.isna()
  assert 0 <= row['rating'] <= 5
  if is_nan['elo']: row['elo'] = default_elo(row['rating'])
  if is_nan['elo_matches']: row['elo_matches'] = 0
  return row


class MetadataManager:
  def __init__(self, img_dir:str, refresh:bool=False, default_elo:Callable[[int], int]=None):
    self.db_fname = os.path.join(img_dir, 'metadata_db.csv')
    metadata_dtypes = {
      'name': str,
      'tags': str,
      'rating': int,
      'elo': int,
      'elo_matches': int,
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
      self.df = self.df.apply(_default_elo, axis=1, args=(default_elo,))
      self.df.sort_values('rating', ascending=False, inplace=True)
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

  def update_elo(self, short_name:str, new_elo:int, new_rating:int) -> None:
    if short_name not in self.df.index:
      raise KeyError(f"{short_name} not in database")
    self.df.loc[short_name, 'elo'] = new_elo
    self.df.loc[short_name, 'elo_matches'] += 1
    assert 0 <= new_rating <= 5
    self.df.loc[short_name, 'rating'] = new_rating
    logging.debug("update_elo(%s, %d): committing", short_name, new_elo)
    logging.debug("%s", self.df.loc[short_name])
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
      "points": int,
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

  def save_boost(self, timestamp:int, name:str, points:int) -> None:
    self.boosts_df.loc[len(self.boosts_df)] = [timestamp, name, points]
    self.boosts_df.to_csv(self.boosts_fname, index=False)


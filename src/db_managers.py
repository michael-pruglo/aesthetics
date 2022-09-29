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
    'stars': stars,
  }


def _default_init(row, default_values_getter):
  assert 0 <= row['stars'], row
  if row.isna()['nmatches']:
    row['nmatches'] = 0
  if default_values_getter:
    for column, value in default_values_getter(row['stars']).items():
      if (column not in row) or pd.isnull(row[column]):
        row[column] = value
      else:
        msg = f"value {row[column]} already exists for {row.index}, will not be overwritten by {value}"
        logging.warning(msg)
  else:
    logging.warning("no default_values_getter was supplied. Ratings are not initialized.")
  return row


class MetadataManager:
  def __init__(self, img_dir:str, refresh:bool=False, defaults_getter:Callable[[int], dict]=None):
    self.db_fname = os.path.join(img_dir, 'metadata_db.csv')
    metadata_dtypes = {
      'name': str,
      'tags': str,
      'stars': float,
      'nmatches': int,
    }
    if os.path.exists(self.db_fname):
      logging.info(f"{self.db_fname} exists, read")
      self.df = pd.read_csv(self.db_fname, keep_default_na=False)
    else:
      logging.info("metadata csv does not exist, create")
      self.df = pd.DataFrame(columns=metadata_dtypes.keys())
    self.df = self.df.astype(metadata_dtypes)
    self.df.set_index('name', inplace=True)

    is_first_run = not os.path.exists(self.db_fname)
    if refresh or is_first_run:
      logging.info("refreshing metadata db...")
      def is_media(fname):
        return fname.find('.')>0 and not fname.endswith('.csv')
      fnames = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if is_media(f)]
      fresh_tagrat = pd.DataFrame(_db_row(fname) for fname in fnames).set_index('name')
      if is_first_run:
        logging.info("first run: creating metadata backup")
        backup_initial_metadata = os.path.join(img_dir, 'backup_initial_metadata.csv')
        fresh_tagrat.to_csv(backup_initial_metadata)
      original_dtypes = self.df.dtypes
      self.df = self.df.combine(fresh_tagrat, lambda old,new: new.fillna(old), overwrite=False)[self.df.columns]
      self.df = self.df.apply(_default_init, axis=1, args=(defaults_getter,))
      self.df = self.df.astype(original_dtypes)
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
    # if short_name not in self.df.index:
    #   raise KeyError(f"{short_name} not in database")
    return self.df.loc[short_name]

  def get_rand_files_info(self, n:int) -> pd.DataFrame:
    return self.df.sample(n)

  def update(self, fullname:str, upd_data:dict, matches_each:int, consensus_stars:float) -> None:
    short_name = short_fname(fullname)
    # if short_name not in self.df.index:
    #   raise KeyError(f"{short_name} not in database")

    row = self.df.loc[short_name].copy()
    if upd_data:
      row.update(upd_data)

    if consensus_stars < 0:
      raise ValueError(f"inappropriate consensus_stars: {consensus_stars}")
    prev_stars = row['stars']
    row.loc['stars'] = consensus_stars
    disk_stars = min(5, int(consensus_stars))
    if min(5, int(prev_stars)) != disk_stars:
      write_metadata(fullname, rating=disk_stars)
      logging.info("file %s updated stars on disk: %f -> %f",
                    short_name, prev_stars, disk_stars)

    row.loc['nmatches'] += matches_each

    self.df.loc[short_name] = row
    logging.debug("updated db: %s", row)

  def on_exit(self):
    self._commit()

  def _get_frequent_tags(self, min_tag_freq):
    lists = self.df['tags'].str.split(' ')
    tag_freq = pd.concat([pd.Series(l) for l in lists], ignore_index=True).value_counts()
    return tag_freq[tag_freq>=min_tag_freq]

  def _commit(self):
    logging.info("commit db to disk")
    self.df.to_csv(self.db_fname)


class HistoryManager:
  def __init__(self, img_dir:str):
    self.matches_fname = os.path.join(img_dir, 'match_history.csv')
    match_history_dtypes = {
      "timestamp": float,
      "name1": str,
      "name2": str,
      "outcome": str,
    }
    if os.path.exists(self.matches_fname):
      logging.info("match_history csv exists, read")
      self.matches_df = pd.read_csv(self.matches_fname, dtype=match_history_dtypes)
      logging.info("%d matches played so far", len(self.matches_df))
    else:
      logging.info("match_history csv does not exist, create")
      self.matches_df = pd.DataFrame(columns=match_history_dtypes.keys())

    self.boosts_fname = os.path.join(img_dir, 'boosts_history.csv')
    boosts_dtypes = {
      "timestamp": float,
      "name": str,
    }
    if os.path.exists(self.boosts_fname):
      logging.info("boosts csv exists, read")
      self.boosts_df = pd.read_csv(self.boosts_fname, dtype=boosts_dtypes)
    else:
      logging.info("boosts csv does not exist, create")
      self.boosts_df = pd.DataFrame(columns=boosts_dtypes.keys())

  def save_match(self, timestamp:float, name1:str, name2:str, outcome:str) -> None:
    self.matches_df.loc[len(self.matches_df)] = [timestamp, name1, name2, outcome]
    self.matches_df.to_csv(self.matches_fname, index=False)

  def save_boost(self, timestamp:float, name:str) -> None:
    self.boosts_df.loc[len(self.boosts_df)] = [timestamp, name]
    self.boosts_df.to_csv(self.boosts_fname, index=False)

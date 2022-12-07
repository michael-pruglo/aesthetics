import logging
import os
import pandas as pd
from typing import Callable
from ae_rater_types import ManualMetadata

from metadata import get_metadata, write_metadata
from helpers import short_fname
from prioritizers import make_prioritizer, PrioritizerType


def get_vocab() -> list[str]:
  fname = os.path.abspath("./tags_vocab.txt")
  if not os.path.exists(fname):
    return None
  with open(fname, "r") as vocab_file:
    return vocab_file.read().split()

def _db_row(fname):
  try:
    meta = get_metadata(fname, get_vocab())
  except:
    meta = ManualMetadata()
    logging.warning("error reading metadata of %s", short_fname(fname))

  def stringify(iterable):
    return ' '.join(sorted(iterable)).lower() if iterable else ""
  return {
    'name': short_fname(fname),
    'tags': stringify(meta.tags),
    'stars': meta.stars,
    'awards': stringify(meta.awards),
  }


def _default_init(row, default_values_getter):
  assert 0 <= row['stars'], row
  if row.isna()['nmatches']:
    row['nmatches'] = 0
  if row.isna()['priority']:
    row['priority'] = 0.8 if row['tags'] else 1
  if row.isna()['awards']:
    row['awards'] = ""
  if default_values_getter:
    for column, value in default_values_getter(row['stars']).items():
      if (column not in row) or pd.isnull(row[column]):
        row[column] = value
      else:
        msg = f"value {row[column]} already exists for {row.name}, will not be overwritten by {value}"
        logging.warning(msg)
  else:
    logging.warning("no default_values_getter was supplied. Ratings are not initialized.")
  return row


class MetadataManager:
  def __init__(self, img_dir:str, refresh:bool=False,
               prioritizer_type:PrioritizerType=PrioritizerType.DEFAULT,
               defaults_getter:Callable[[int], dict]=None):
    self.db_fname = os.path.join(img_dir, 'metadata_db.csv')
    self.matches_since_last_save = 0
    metadata_dtypes = {
      'name': str,
      'tags': str,
      'stars': float,
      'nmatches': int,
      'priority': float,
      'awards': str,
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
      def is_media(fname:str):
        return fname.find('.')>0 and not fname.endswith(('.csv', '.pkl'))
      fnames = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if is_media(f)]
      fresh_tagrat = pd.DataFrame(_db_row(fname) for fname in fnames).set_index('name')
      if is_first_run:
        logging.info("first run: creating metadata backup")
        backup_initial_metadata = os.path.join(img_dir, 'backup_initial_metadata.csv')
        fresh_tagrat.to_csv(backup_initial_metadata)
      original_dtypes = self.df.dtypes
      joined = self.df.join(fresh_tagrat, how='right', lsuffix='_old')

      def refresh_row(row):
        if not row.isna()['stars_old']:
          if int(row['stars']) == int(row['stars_old']):
            row['stars'] = row['stars_old']
        return row
      self.df = joined.apply(refresh_row, axis=1)[self.df.columns]
      self.df = self.df.apply(_default_init, axis=1, args=(defaults_getter,))
      self.df = self.df.astype(original_dtypes)
      self.df.sort_values('stars', ascending=False, inplace=True)
      self._commit()

    self.prioritizer = make_prioritizer(prioritizer_type)
    self.df = self.df.apply(self.prioritizer.calc, axis=1)

  def get_db(self, min_tag_freq:int=0) -> pd.DataFrame:
    if min_tag_freq:
      freq_tags = self._get_frequent_tags(min_tag_freq)
      logging.debug("frequency of tags (threshold %d):\n%s", min_tag_freq, freq_tags)
      dfc = self.df.copy()
      def remove_infrequent(s):
        return ' '.join([tag for tag in s.split(' ') if tag in freq_tags])
      dfc['tags'] = dfc['tags'].apply(remove_infrequent)
      return dfc

    return self.df

  def get_tags_vocab(self) -> list[str]:
    return get_vocab()

  def get_file_info(self, short_name:str) -> pd.Series:
    return self.df.loc[short_name]

  def get_rand_files_info(self, n:int) -> pd.DataFrame:
    return self.df.sample(n, weights='priority')

  def get_search_results(self, query:str) -> pd.DataFrame:
    query = query.strip()
    if query == "":
      return self.df

    def negpos(subquery:str) -> tuple:
      neg, pos = [], []
      for word in subquery.split():
        if word.startswith('-'):
          neg.append(word[1:])
        else:
          pos.append(word)
      return neg, pos
    subqueries = [negpos(sub) for sub in query.split('|')]
    def is_match(row:pd.Series) -> bool:
      row['name'] = row.name
      strrow = row.astype(str).str
      for neg_filters, pos_filters in subqueries:
        pos = [strrow.contains(word).any() for word in pos_filters]
        neg = [strrow.contains(word).any() for word in neg_filters]
        if all(pos) and not any(neg):
          return True
      return False

    return self.df[self.df.apply(is_match, axis=1)]

  def update(self, fullname:str, upd_data:dict, matches_each:int=0) -> None:
    short_name = short_fname(fullname)
    row = self.df.loc[short_name].copy()

    # updates on disk
    new_disk_tags = None
    if 'tags' in upd_data:
      new_disk_tags = upd_data['tags'].split()
    new_disk_awards = None
    if 'awards' in upd_data:
      new_disk_awards = upd_data['awards'].split()
    new_disk_stars = None
    if 'stars' in upd_data:
      if upd_data['stars'] < 0:
        raise ValueError(f"inappropriate consensus_stars: {upd_data['stars']}")
      prev_stars = row['stars']
      new_disk_stars = min(5, int(upd_data['stars']))
      if min(5, int(prev_stars)) != new_disk_stars:
        logging.info("file %s updated stars on disk: %f -> %f",
                      short_name, prev_stars, new_disk_stars)
      else:
        new_disk_stars = None
    new_disk_meta = ManualMetadata(new_disk_tags, new_disk_stars, new_disk_awards)
    write_metadata(fullname, new_disk_meta, append=False)

    # updates in df
    if upd_data:
      row.update(upd_data)
    row.loc['nmatches'] += matches_each
    row = self.prioritizer.calc(row)
    self.df.loc[short_name] = row
    logging.debug("updated db: %s", row)

    self.matches_since_last_save += 1
    if self.matches_since_last_save > 7:
      self._commit()
      self.matches_since_last_save = 0

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
      "names": str,
      "outcome": str,
    }
    if os.path.exists(self.matches_fname):
      logging.info("match_history csv exists, read")
      self.matches_df = pd.read_csv(self.matches_fname, dtype=match_history_dtypes)
      logging.info("%d matches played so far", len(self.matches_df))
    else:
      logging.info("match_history csv does not exist, create")
      self.matches_df = pd.DataFrame(columns=match_history_dtypes.keys())

  def save_match(self, timestamp:float, names:list[str], outcome:str) -> None:
    self.matches_df.loc[len(self.matches_df)] = [timestamp, names, outcome]
    self.matches_df.to_csv(self.matches_fname, index=False)

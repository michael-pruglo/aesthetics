import logging
import os
import pandas as pd
from typing import Callable

from metadata import ManualMetadata, get_metadata, write_metadata
import helpers as hlp
from prioritizers import make_prioritizer, PrioritizerType


def stringify(iterable):
  return ' '.join(sorted(iterable)).lower() if iterable else ""

def _db_row(fname):
  meta = get_metadata(fname)
  return {
    'name': hlp.short_fname(fname),
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
    logging.warning("no default_values_getter was supplied. Ratings are not initialized.")
  return row


class MetadataManager:
  def __init__(self, img_dir:str, refresh:bool=False,
               prioritizer_type:PrioritizerType=PrioritizerType.DEFAULT,
               defaults_getter:Callable=None):
    self.db_fname = os.path.join(img_dir, 'metadata_db.csv')
    self.initial_metadata_fname = os.path.join(img_dir, 'backup_initial_metadata.csv')
    self.media_dir = img_dir
    self.profile_updates_since_last_save = 0
    self.defaults_getter = defaults_getter
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
      if not os.path.exists(self.initial_metadata_fname):
        logging.info("creating metadata backup")
        fresh_tagrat.to_csv(self.initial_metadata_fname)
      original_dtypes = self.df.dtypes
      joined = self.df.join(fresh_tagrat, how='right', lsuffix='_old')

      def refresh_row(row):
        if not row.isna()['stars_old']:
          if int(row['stars']) == int(row['stars_old']):
            row['stars'] = row['stars_old']
        return row
      self.df = joined.apply(refresh_row, axis=1)[self.df.columns]
      self.df = self.df.apply(_default_init, axis=1, args=(self.defaults_getter,))
      self.df = self.df.astype(original_dtypes)
      self.df.sort_values('stars', ascending=False, inplace=True)
      self._commit()

    self.set_prioritizer(prioritizer_type)

  def set_prioritizer(self, prioritizer_type) -> None:
    self.prioritizer = make_prioritizer(prioritizer_type)
    self.df = self.df.apply(self.prioritizer.calc, axis=1)

  def reset_meta_to_initial(self):
    df = pd.read_csv(self.initial_metadata_fname)
    for _, row in df.iterrows():
      fullname = os.path.join(self.media_dir, row['name'])
      if not os.path.exists(fullname):
        continue
      reset_data = {
        'tags': row['tags'],
        'stars': row['stars'],
        'awards': row['awards'],
        'nmatches': 0,
      }
      reset_data |= self.defaults_getter(row['stars'])
      self.update(fullname, reset_data)

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

  def get_file_info(self, short_name:str) -> pd.Series:
    return self.df.loc[short_name]

  def get_rand_files_info(self, n:int) -> pd.DataFrame:
    return self.df.sample(n, weights='priority')

  def get_search_results(self, query:str, n_per_page:int, page:int=1) -> pd.DataFrame:
    query = query.strip()
    hit_idx = 0
    if query == "":
      return self.df[n_per_page*(page-1):n_per_page*page]

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
      nonlocal hit_idx
      if hit_idx > n_per_page*page:
        return False
      row['name'] = row.name
      strrow = row.astype(str).str
      for neg_filters, pos_filters in subqueries:
        pos = [strrow.contains(word).any() for word in pos_filters]
        neg = [strrow.contains(word).any() for word in neg_filters]
        if all(pos) and not any(neg):
          hit_idx += 1
          return n_per_page*(page-1) < hit_idx <= n_per_page*page
      return False

    return self.df[self.df.apply(is_match, axis=1)]

  def update(self, fullname:str, upd_data:dict, matches_each:int=0) -> None:
    # TODO: to improve performance,
    # accept updates in bulk - in dataframes (from apply_opinions and reset_meta)
    logging.debug("DB update():\n%s\n%s\nmatches_each=%d\n", fullname, upd_data, matches_each)
    short_name = hlp.short_fname(fullname)
    row = self.df.loc[short_name].copy()

    if 'stars' in upd_data:
      assert upd_data['stars'] >= 0, upd_data

    # updates in df
    if upd_data:
      row.update(upd_data)
    row.loc['nmatches'] += matches_each
    row = self.prioritizer.calc(row)
    self.df.loc[short_name] = row
    logging.debug("updated db: %s", row)

    # updates on disk
    # TODO: to improve performance,
    # maybe queue all write_metadata calls (create a set of changed fullnames),
    # and only do the disk write operations on _commit()
    # in that case, be careful that the whole program uses the freshest info from the DF, and not disk
    new_disk_meta = ManualMetadata.from_str(row['tags'], int(row['stars']), row['awards'])
    write_metadata(fullname, new_disk_meta)

    self.profile_updates_since_last_save += 1
    if self.profile_updates_since_last_save > 20:
      self._commit()
      self.profile_updates_since_last_save = 0

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
  def __init__(self, img_dir:str, history_fname:str):
    self.matches_fname = os.path.join(img_dir, history_fname)
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

  def get_match_history(self):
    return self.matches_df

import logging
from typing import Callable
from libxmp import XMPFiles, consts


def get_metadata(fname:str) -> tuple[list, int]:
  xmpfile = XMPFiles(file_path=fname)
  xmp = xmpfile.get_xmp()
  if xmp is None:
    raise RuntimeError(f"file {fname} has no xmp")
  xmpfile.close_file()

  def get_tags():
    propname = (consts.XMP_NS_Lightroom, "hierarchicalSubject")
    if not xmp.does_property_exist(*propname):
      logging.warning("no hierarchical tags in %s", fname.split('/')[-1])
      propname = (consts.XMP_NS_DC, "subject")
      if not xmp.does_property_exist(*propname):
        logging.error("No tags in metadata of %s", fname.split('/')[-1])
        return []
    n = xmp.count_array_items(*propname)
    if n==0:
      logging.warning("ZERO tags in %s", fname.split('/')[-1])
    return [xmp.get_array_item(*propname, i+1) for i in range(n)]

  def get_rating():
    propname = (consts.XMP_NS_XMP, "Rating")
    if not xmp.does_property_exist(*propname):
      return 0

    return xmp.get_property_int(*propname)

  return get_tags(), get_rating()

def write_metadata(fname:str, tags:list=None, rating:int=None) -> None:
  xmpfile = XMPFiles(file_path=fname, open_forupdate=True)
  xmp = xmpfile.get_xmp()
  if not xmpfile.can_put_xmp(xmp):
    raise RuntimeError(f"file {fname}: metadata not writable")

  if tags is not None:
    for tag in tags:
      hier_prop = (consts.XMP_NS_Lightroom, "hierarchicalSubject", tag)
      if xmp.does_array_item_exist(*hier_prop):
        logging.warning("%s: hier already exists '%s'", fname.split('/')[-1], tag)
      else:
        xmp.append_array_item(*hier_prop, {'prop_array_is_ordered': False, 'prop_value_is_array': True})
      subj_prop = (consts.XMP_NS_DC, "subject", tag.split('|')[-1])
      if xmp.does_array_item_exist(*subj_prop):
        logging.warning("%s: subj already exists '%s'", fname.split('/')[-1], tag.split('|')[-1])
      else:
        xmp.append_array_item(*subj_prop, {'prop_array_is_ordered': False, 'prop_value_is_array': True})

  if rating is not None:
    r_prop = (consts.XMP_NS_XMP, "Rating")
    xmp.set_property_int(*r_prop, rating)

  xmpfile.put_xmp(xmp)
  xmpfile.close_file()



from PIL import Image

def get_metadata2(fname):
  not_image = fname.split('.')[-1].lower() in ['mp4', 'gif', 'mov']
  if not_image:
    return [], -1

  try:
    with Image.open(fname) as im:
      xmp = im.getxmp()
      desc = xmp['xmpmeta']['RDF']['Description']

      tags = []
      if (hier:='hierarchicalSubject') in desc.keys():
        tags = desc[hier]['Bag']['li']
      elif (fmt:='format') in desc.keys():
        logging.warning("no hierarchical tags in %s", fname)
        tags = desc[fmt]['Bag']['li']
      else:
        raise RuntimeError(f'No XMP tags in {fname}')

      rating = -1
      if (rat:='Rating') in desc.keys():
        rating = int(desc[rat])
      else:
        rating = 0

      return tags, rating
  except Exception as error:
    logging.error("could not open %s: %s", fname, error)
    return [], -2



import os
import pandas as pd

def _db_row(fname):
  tags, rating = get_metadata(fname)
  return {
    'name': fname.split('/')[-1],
    'tags': ' '.join(sorted(tags)).lower(),
    'rating': int(rating),
  }

def _default_elo(row, default_elo:Callable[[int], int]):
  is_nan = row.isna()
  assert 0 <= row['rating'] <= 5
  if is_nan['elo']: row['elo'] = default_elo(row['rating'])
  if is_nan['elo_matches']: row['elo_matches'] = 0
  return row

class MetadataManager():
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
      logging.info("csv exists, read")
      self.df = pd.read_csv(self.db_fname, keep_default_na=False, dtype=metadata_dtypes)
    else:
      logging.info("csv does not exist, create")
      self.df = pd.DataFrame(columns=metadata_dtypes.keys())
    self.df.set_index('name', inplace=True)

    if refresh or not os.path.exists(self.db_fname):
      logging.info("refreshing db...")
      def is_media(fname):
        return fname.find('.')>0 and not fname.endswith('.csv')
      fnames = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if is_media(f)]
      fresh_tagrat = pd.DataFrame(_db_row(fname) for fname in fnames).set_index('name')
      self.df = self.df.combine(fresh_tagrat, lambda old,new: new.fillna(old), overwrite=False)[self.df.columns]
      self.df = self.df.apply(_default_elo, args=(default_elo), axis=1)
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

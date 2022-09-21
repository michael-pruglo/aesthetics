import unittest
import os
import pandas as pd

from src.metadata import get_metadata
from src.db_managers import *


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")


class TestMetadataManager(unittest.TestCase):
  def setUp(self) -> None:
    assert os.path.exists(MEDIA_FOLDER)
    self.nfiles = len([f for f in os.listdir(MEDIA_FOLDER)
                       if os.path.isfile(os.path.join(MEDIA_FOLDER, f))
                       and f.split('.')[-1] != 'csv'])
    assert self.nfiles > 2
    self.metafile = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
    self.assertFalse(os.path.exists(self.metafile))

  def tearDown(self) -> None:
    if os.path.exists(self.metafile):
      os.remove(self.metafile)

  def _check_db(self, db:pd.DataFrame, expected_len:int):
    self.assertEqual(len(db), expected_len)
    self.assertTrue({'tags','stars','nmatches'}.issubset(db.columns))
    self.assertTrue((db['tags'].notna()).all())
    self.assertTrue((db['stars'].between(0,5)).all())
    self.assertTrue((db['nmatches']==0).all())
    for short_name, row in db.sample(len(db)//5).iterrows():
      fname = os.path.join(MEDIA_FOLDER, short_name)
      self.assertTrue(os.path.exists(fname))
      expected_metadata = get_metadata(fname)
      given_metadata = ({t for t in row['tags'].split()}, row['stars'])
      self.assertTupleEqual(given_metadata, expected_metadata, short_name)

  def test_init_fresh(self):
    mm = MetadataManager(MEDIA_FOLDER)
    self.assertTrue(os.path.exists(self.metafile))
    self._check_db(mm.get_db(), self.nfiles)

  def test_init_existing_csv(self):
    mm0 = MetadataManager(MEDIA_FOLDER)
    self.assertTrue(os.path.exists(self.metafile))

    # make sure next manager reads db from disk, doesn't create anew
    db0 = mm0.get_db()
    CANARIES = 2
    pd.concat([db0, db0.sample(CANARIES)]).to_csv(self.metafile)

    mm = MetadataManager(MEDIA_FOLDER)
    self._check_db(mm.get_db(), self.nfiles+CANARIES)

  def test_init_updated_files_no_refresh(self):
    pass

  def test_init_updated_files_refresh(self):
    pass


if __name__ == '__main__':
  unittest.main()

import unittest
import os
import random
import shutil
import pandas as pd

from src.metadata import get_metadata
from src.db_managers import *


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
BACKUP_FOLDER = os.path.join(MEDIA_FOLDER, "bak/")
IMMITATED_CHANGES = 3


class TestMetadataManager(unittest.TestCase):
  def setUp(self) -> None:
    assert os.path.exists(MEDIA_FOLDER)
    self.initial_files = [f for f in os.listdir(MEDIA_FOLDER)
                       if os.path.isfile(os.path.join(MEDIA_FOLDER, f))
                       and f.split('.')[-1] != 'csv']
    assert len(self.initial_files) > 2
    self.metafile = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
    assert not os.path.exists(self.metafile)

  def tearDown(self) -> None:
    if os.path.exists(self.metafile):
      os.remove(self.metafile)
    if os.path.exists(BACKUP_FOLDER):
      for f in os.listdir(BACKUP_FOLDER):
        shutil.move(os.path.join(BACKUP_FOLDER, f), os.path.join(MEDIA_FOLDER, f))
      os.rmdir(BACKUP_FOLDER)

  def _create_mgr(self, *args, **kwargs) -> MetadataManager:
    mm = MetadataManager(MEDIA_FOLDER, *args, **kwargs)
    self.assertTrue(os.path.exists(self.metafile))
    return mm

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

  def _immitate_external_metadata_change(self):
    files = [os.path.join(MEDIA_FOLDER, f)
             for f in random.sample(self.initial_files, IMMITATED_CHANGES)]
    if not os.path.exists(BACKUP_FOLDER):
      os.mkdir(BACKUP_FOLDER)
    for f in files:
      shutil.copy(f, BACKUP_FOLDER)
    write_metadata(files[0], tags=["canary", "canary|tagcanary"])
    write_metadata(files[1], rating=5-get_metadata(files[1])[1])
    write_metadata(files[2], tags=["finch", "finch|tagfi"], rating=5-get_metadata(files[2])[1])

  def test_init_fresh(self):
    mm = self._create_mgr()
    self._check_db(mm.get_db(), len(self.initial_files))

  def test_init_existing_csv(self):
    mm0 = self._create_mgr()

    # make sure next manager reads db from disk, doesn't create anew
    db0 = mm0.get_db()
    CANARIES = 2
    pd.concat([db0, db0.sample(CANARIES)]).to_csv(self.metafile)

    mm = self._create_mgr()
    self._check_db(mm.get_db(), len(self.initial_files)+CANARIES)

  def test_init_updated_files_no_refresh(self):
    mm0 = self._create_mgr()
    db0 = mm0.get_db()
    self._immitate_external_metadata_change()
    mm1 = self._create_mgr()
    self.assertTrue(mm1.get_db().equals(db0))

  def test_init_updated_files_refresh(self):
    mm0 = self._create_mgr()
    db0 = mm0.get_db()
    self._immitate_external_metadata_change()
    mm1 = self._create_mgr(refresh=True)
    db1 = mm1.get_db()
    self.assertFalse(db1.equals(db0))
    diff = (db1.sort_index().compare(db0.sort_index()))
    self.assertTupleEqual(diff.shape, (IMMITATED_CHANGES,2*2), diff)


if __name__ == '__main__':
  unittest.main()

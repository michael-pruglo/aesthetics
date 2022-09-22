import unittest
import os
import random
import shutil
import pandas as pd

from src.metadata import get_metadata
from src.db_managers import *


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
BACKUP_FOLDER = os.path.join(MEDIA_FOLDER, "bak/")
EXTRA_FOLDER = os.path.join(MEDIA_FOLDER, "extra/")


def defgettr(stars:int) -> dict:
  return {"elo":1200+stars, "glicko":1500+stars, "tst":stars*10}


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
    if os.path.exists(EXTRA_FOLDER):
      for f in os.listdir(EXTRA_FOLDER):
        extra_file = os.path.join(MEDIA_FOLDER, f)
        if os.path.exists(extra_file):
          os.remove(extra_file)

  def _create_mgr(self, *args, **kwargs) -> MetadataManager:
    mm = MetadataManager(MEDIA_FOLDER, *args, **kwargs)
    self.assertTrue(os.path.exists(self.metafile))
    return mm

  def _check_db(self, db:pd.DataFrame, expected_len:int) -> None:
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

  def _immitate_external_metadata_change(self) -> int:
    num_files = 3
    files = [os.path.join(MEDIA_FOLDER, f)
             for f in random.sample(self.initial_files, num_files)]
    if not os.path.exists(BACKUP_FOLDER):
      os.mkdir(BACKUP_FOLDER)
    for f in files:
      shutil.copy(f, BACKUP_FOLDER)
    write_metadata(files[0], tags=["canary", "canary|tagcanary"])
    write_metadata(files[1], rating=5-get_metadata(files[1])[1])
    write_metadata(files[2], tags=["finch", "finch|tagfi"], rating=5-get_metadata(files[2])[1])
    return num_files

  def _add_extra_files(self) -> int:
    for f in os.listdir(EXTRA_FOLDER):
      fullname = os.path.join(EXTRA_FOLDER, f)
      assert os.path.isfile(fullname)
      shutil.copy(fullname, MEDIA_FOLDER)
    return len(os.listdir(EXTRA_FOLDER))

  def _test_external_change(self, update_existing=False, add_new=False,
                            refresh=False, defgettr=None) -> None:
    db0 = self._create_mgr(defaults_getter=defgettr).get_db()
    if update_existing:
      changed_amount = self._immitate_external_metadata_change()
    if add_new:
      extra_amount = self._add_extra_files()
    db1 = self._create_mgr(refresh=refresh, defaults_getter=defgettr).get_db()

    self.assertTrue(db1.notna().all(axis=None))
    if not refresh:
      self.assertTrue(db1.equals(db0))
    else:
      old_rows = db1.index.isin(db0.index)
      old_portion, new_portion = db1.loc[old_rows], db1.loc[~old_rows]
      if update_existing:
        diff = (old_portion.sort_index().compare(db0.sort_index()))
        err_msg = f"should update only tags and rating, leaving others untouched:\n{diff}"
        self.assertTupleEqual(diff.shape, (changed_amount,2*2), err_msg)
      else:
        self.assertTrue(old_portion.sort_index().equals(db0.sort_index()))
      if add_new:
        self._check_db(new_portion, extra_amount)


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

  def test_init_no_refresh(self):            self._test_external_change(True, True, False)
  def test_init_updated_files(self):         self._test_external_change(True, False, True)
  def test_init_extra_files(self):           self._test_external_change(False, True, True)
  def test_init_updated_and_extra(self):     self._test_external_change(True, True, True)
  def test_defgettr_no_refresh(self):        self._test_external_change(True, True, False, defgettr)
  def test_defgettr_updated_files(self):     self._test_external_change(True, False, True, defgettr)
  def test_defgettr_extra_files(self):       self._test_external_change(False, True, True, defgettr)
  def test_defgettr_updated_and_extra(self): self._test_external_change(True, True, True, defgettr)


if __name__ == '__main__':
  unittest.main()

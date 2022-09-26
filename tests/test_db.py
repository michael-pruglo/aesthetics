import unittest
import os
import random
import pandas as pd

from src.metadata import get_metadata
from src.db_managers import MetadataManager
import tests.helpers as hlp
from tests.helpers import BACKUP_INITIAL_FILE, MEDIA_FOLDER, METAFILE


def defgettr(stars) -> dict:
  stars = int(stars)
  return {"elo":1200+stars, "glicko":1500+stars, "tst":stars*10}


class TestMetadataManager(unittest.TestCase):
  def setUp(self) -> None:
    assert os.path.exists(MEDIA_FOLDER)
    assert not os.path.exists(METAFILE)
    self.initial_files = hlp.get_initial_mediafiles()
    self.nfiles = len(self.initial_files)
    assert self.nfiles > 2

  def tearDown(self) -> None:
    hlp.disk_cleanup()

  def _create_mgr(self, *args, **kwargs) -> MetadataManager:
    mm = MetadataManager(MEDIA_FOLDER, *args, **kwargs)
    self.assertTrue(os.path.exists(METAFILE))
    self.assertTrue(os.path.exists(BACKUP_INITIAL_FILE))
    return mm

  def _check_row(self, short_name:str, row:pd.Series) -> None:
    self.assertTrue({'tags','stars','nmatches'}.issubset(row.index))
    fname = os.path.join(MEDIA_FOLDER, short_name)
    self.assertTrue(os.path.exists(fname))
    expected_metadata = get_metadata(fname)
    given_metadata = ({t for t in row['tags'].split()}, int(row['stars']))
    self.assertTupleEqual(given_metadata, expected_metadata, short_name)

  def _check_db(self, db:pd.DataFrame, expected_len:int) -> None:
    self.assertEqual(len(db), expected_len)
    self.assertTrue({'tags','stars','nmatches'}.issubset(db.columns))
    self.assertTrue((db['tags'].notna()).all())
    self.assertTrue((db['stars'].ge(0)).all())
    self.assertTrue((db['nmatches']==0).all())
    for short_name, row in db.sample(len(db)//5).iterrows():
      self._check_row(short_name, row)

  def _test_external_change(self, update_existing=False, add_new=False,
                            refresh=False, defgettr=None) -> None:
    db0 = self._create_mgr(defaults_getter=defgettr).get_db()
    if update_existing:
      changed_amount = hlp.immitate_external_metadata_change()
    if add_new:
      extra_amount = hlp.inject_extra_files()
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
    self._check_db(mm.get_db(), self.nfiles)

  def test_init_existing_csv(self):
    mm0 = self._create_mgr()

    # make sure next manager reads db from disk, doesn't create anew
    db0 = mm0.get_db()
    CANARIES = 2
    pd.concat([db0, db0.sample(CANARIES)]).to_csv(METAFILE)

    mm = self._create_mgr()
    self._check_db(mm.get_db(), self.nfiles+CANARIES)

  def test_init_no_refresh(self):            self._test_external_change(True, True, False)
  def test_init_updated_files(self):         self._test_external_change(True, False, True)
  def test_init_extra_files(self):           self._test_external_change(False, True, True)
  def test_init_updated_and_extra(self):     self._test_external_change(True, True, True)
  def test_defgettr_no_refresh(self):        self._test_external_change(True, True, False, defgettr)
  def test_defgettr_updated_files(self):     self._test_external_change(True, False, True, defgettr)
  def test_defgettr_extra_files(self):       self._test_external_change(False, True, True, defgettr)
  def test_defgettr_updated_and_extra(self): self._test_external_change(True, True, True, defgettr)

  def test_get_info(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    with self.assertRaises(KeyError):
      mm.get_file_info("NONEXISTENT")
    for short_name in random.sample(self.initial_files, 4):
      self._check_row(short_name, mm.get_file_info(short_name))

  def test_update_raises(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    with self.assertRaises(KeyError):
      mm.update("NONEXISTENT", {'elo':1230, 'glicko':1400}, 2, 4)
    with self.assertRaises(ValueError):
      fullname = os.path.join(MEDIA_FOLDER, random.choice(self.initial_files))
      mm.update(fullname, upd_data={}, is_match=random.randint(0,1), consensus_stars=-1)

  def test_update_stars(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    tst_updates = []
    for short_name in random.sample(self.initial_files, self.nfiles//3):
      fullname = os.path.join(MEDIA_FOLDER, short_name)
      disk_tags_before, disk_stars_before = get_metadata(fullname)
      row_before = mm.get_file_info(short_name)
      if random.randint(0,1):
        upd_stars = 5 - disk_stars_before + random.randint(1,9)/10
        tst_updates.append((short_name, upd_stars))
      else:
        upd_stars = disk_stars_before
      inc_match = random.randint(0,1)

      hlp.backup_files([fullname])
      mm.update(fullname, upd_data={}, is_match=inc_match, consensus_stars=upd_stars)

      disk_tags_after, disk_stars_after = get_metadata(fullname)
      self.assertSetEqual(disk_tags_before, disk_tags_after, short_name)
      if upd_stars is None:
        self.assertEqual(disk_stars_after, disk_stars_before, short_name)
      else:
        self.assertEqual(disk_stars_after, int(upd_stars), short_name)

      row_after = mm.get_file_info(short_name)
      self._check_row(short_name, row_after)
      self.assertEqual(row_after['nmatches'], row_before['nmatches']+inc_match)

    mm1 = self._create_mgr(defaults_getter=defgettr)
    for short_name, stars in tst_updates:
      row_next_run = mm1.get_file_info(short_name)
      self.assertEqual(row_next_run['stars'], stars)

  def test_update_rating(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    tst_updates = []
    for short_name in random.sample(self.initial_files, self.nfiles//3):
      fullname = os.path.join(MEDIA_FOLDER, short_name)
      row_before = mm.get_file_info(short_name)
      is_boost = random.randint(0,1)
      val_updates = {col:random.randint(0,2000)
                     for col in random.sample(["elo","glicko","tst"], random.randint(1,3))}

      hlp.backup_files([fullname])
      mm.update(fullname, upd_data=val_updates, is_match=not is_boost, consensus_stars=row_before['stars'])

      row_after = mm.get_file_info(short_name)
      self.assertEqual(row_after['nmatches'], row_before['nmatches']+(not is_boost))
      for col, given_val in row_after.items():
        expected_val = val_updates[col] if col in val_updates else row_before[col]
        if col=='nmatches':
          expected_val += not is_boost
        self.assertEqual(given_val, expected_val, f"for column '{col}'")
      tst_updates.append((short_name, row_after))

    mm1 = self._create_mgr(defaults_getter=defgettr)
    for short_name, row_after in tst_updates:
      row_next_run = mm1.get_file_info(short_name)
      self.assertTrue(row_next_run.equals(row_after))


if __name__ == '__main__':
  unittest.main()

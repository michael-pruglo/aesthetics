import string
import unittest
import os
import random
import pandas as pd
from pandas import testing as tm
from ae_rater_model import DBAccess
from ae_rater_types import ManualMetadata, MatchInfo, Outcome, ProfileInfo
from prioritizers import PrioritizerType
from rating_backends import ELO, Glicko

from src.metadata import get_metadata
from src.db_managers import MetadataManager
from src.helpers import short_fname
import tests.helpers as hlp
from tests.helpers import BACKUP_INITIAL_FILE, MEDIA_FOLDER, METAFILE


def is_sorted(l:list[ProfileInfo]) -> bool:
  for i, curr_prof in enumerate(l[:-1]):
    next_prof = l[i+1]
    if curr_prof.stars < next_prof.stars:
      return False
    if all(curr_prof.ratings[s].points < next_prof.ratings[s].points
           for s in curr_prof.ratings.keys()):
      return False
  return True

def defgettr(stars) -> dict:
  stars = int(stars)
  return {"elo":1200+stars, "glicko":1500+stars, "tst":stars*10}


class TestDBAccess(unittest.TestCase):
  def setUp(self):
    self.dba = DBAccess(MEDIA_FOLDER, refresh=False, prioritizer_type=PrioritizerType.DEFAULT, rat_systems=[Glicko(),ELO()])

  def tearDown(self):
    hlp.disk_cleanup()

  def test_match_generation(self):
    def all_unique(li):
      seen = list()
      return not any(i in seen or seen.append(i) for i in li)
    for i in range(2,25):
      participants = self.dba.get_next_match(i)
      self.assertTrue(all_unique(participants))

  def test_get_leaderboard(self):
    ldbrd = self.dba.get_leaderboard()
    mediafiles = hlp.get_initial_mediafiles()
    self.assertTrue(is_sorted(ldbrd))
    self.assertSetEqual({short_fname(p.fullname) for p in ldbrd}, set(mediafiles))

  def test_get_match_history(self):
    mock_history = []
    for _ in range(random.randint(4,21)):
      n = random.randint(2,10)
      participants = self.dba.get_next_match(n)
      outcome_str = string.ascii_lowercase[:n] + " "*random.randint(n//2,n)
      outcome_str = ''.join(random.sample(outcome_str, len(outcome_str)))
      mock_history.append(MatchInfo(participants, Outcome(outcome_str)))
    for match in mock_history:
      self.dba.save_match(match)
    self.assertListEqual(self.dba.get_match_history(), mock_history)

  def test_apply_opinions(self):
    pass

  def test_meta_update(self):
    pass


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
    given_metadata = ManualMetadata(
      {t for t in row['tags'].split()} or None,
      int(row['stars']),
      {a for a in row['awards'].split()} or None,
    )
    self.assertEqual(given_metadata, expected_metadata, short_name)

  def _check_db(self, db:pd.DataFrame, expected_len:int) -> None:
    self.assertEqual(len(db), expected_len)
    self.assertTrue({'tags','stars','nmatches'}.issubset(db.columns))
    self.assertTrue((db['tags'].notna()).all())
    self.assertTrue((db['stars'].ge(0)).all())
    self.assertTrue((db['nmatches']==0).all())
    for short_name, row in db.sample(len(db)//5).iterrows():
      self._check_row(short_name, row)

  def _test_external_change(self, update_existing=False, add_new=False,
                            refresh=False, remove_some=False, defgettr=None) -> None:
    mm0 = self._create_mgr(defaults_getter=defgettr)
    db0 = mm0.get_db()
    rm_amount = 0
    if remove_some:
      rm_amount = hlp.remove_some_files()
    if update_existing:
      for f in db0.index:
        fullname = os.path.join(MEDIA_FOLDER, f)
        mm0.update(fullname, {'stars':db0.loc[f,'stars']+.6}, 0)
      mm0._commit()
      db0 = mm0.get_db()
      tags_changed, stars_changed = hlp.immitate_external_metadata_change()
    if add_new:
      extra_amount = hlp.inject_extra_files()
    db1 = self._create_mgr(refresh=refresh, defaults_getter=defgettr).get_db()

    self.assertTrue(db1.notna().all(axis=None))
    if not refresh:
      self.assertTrue(db1.drop('priority',axis=1).equals(db0.drop('priority',axis=1)))
    else:
      old_rows = db1.index.isin(db0.index)
      old_portion, new_portion = db1.loc[old_rows], db1.loc[~old_rows]
      self.assertEqual(len(old_portion), len(db0)-rm_amount)
      if update_existing:
        diff = (old_portion.sort_index().compare(db0.sort_index()))
        err_msg = f"db0:\n{db0}\n\ndb1\n{db1}\n\ndiff\n{diff}"
        self.assertEqual(len(diff['tags'].dropna()), tags_changed, err_msg)
        self.assertEqual(len(diff['stars'].dropna()), stars_changed, diff['stars'])
      else:
        diffset = set(db0.index) - set(old_portion.index)
        self.assertEqual(len(diffset), rm_amount)
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
  def test_deletions(self):                  self._test_external_change(False, False, True, True)
  def test_defgettr_no_refresh(self):        self._test_external_change(True, True, False, False, defgettr)
  def test_defgettr_updated_files(self):     self._test_external_change(True, False, True, False, defgettr)
  def test_defgettr_extra_files(self):       self._test_external_change(False, True, True, False, defgettr)
  def test_defgettr_updated_and_extra(self): self._test_external_change(True, True, True, False, defgettr)

  def test_get_info(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    with self.assertRaises(KeyError):
      mm.get_file_info("NONEXISTENT")
    for short_name in random.sample(self.initial_files, 4):
      self._check_row(short_name, mm.get_file_info(short_name))

  def test_update_stars(self):
    mm = self._create_mgr(defaults_getter=defgettr)
    tst_updates = []
    for short_name in random.sample(self.initial_files, self.nfiles//3):
      fullname = os.path.join(MEDIA_FOLDER, short_name)
      disk_meta_before = get_metadata(fullname)
      row_before = mm.get_file_info(short_name)
      if random.randint(0,1):
        upd_stars = 5 - disk_meta_before.stars + random.randint(1,9)/10
        tst_updates.append((short_name, upd_stars))
      else:
        upd_stars = disk_meta_before.stars
      inc_match = random.randint(0,17)

      hlp.backup_files([fullname])
      mm.update(fullname, upd_data={'stars':upd_stars}, matches_each=inc_match)

      disk_meta_after = get_metadata(fullname)
      self.assertSetEqual(disk_meta_before.tags, disk_meta_after.tags, short_name)
      self.assertEqual(disk_meta_before.awards, disk_meta_after.awards, short_name)
      if upd_stars is None:
        self.assertEqual(disk_meta_after.stars, disk_meta_before.stars, short_name)
      else:
        self.assertEqual(disk_meta_after.stars, int(upd_stars), short_name)

      row_after = mm.get_file_info(short_name)
      self._check_row(short_name, row_after)
      self.assertEqual(row_after['nmatches'], row_before['nmatches']+inc_match)
    mm.on_exit()

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
      matches_each = random.randint(0,17)
      val_updates = {col:random.randint(0,2000)
                     for col in random.sample(["elo","glicko","tst"], random.randint(1,3))}
      val_updates['stars'] = row_before['stars']

      hlp.backup_files([fullname])
      mm.update(fullname, upd_data=val_updates, matches_each=matches_each)

      row_after = mm.get_file_info(short_name)
      for col, given_val in row_after.items():
        expected_val = val_updates[col] if col in val_updates else row_before[col]
        if col=='nmatches':
          expected_val += matches_each
        if col!='priority':
          self.assertEqual(given_val, expected_val, f"for column '{col}'")
      tst_updates.append((short_name, row_after))
    mm.on_exit()

    mm1 = self._create_mgr(defaults_getter=defgettr)
    for short_name, row_after in tst_updates:
      row_next_run = mm1.get_file_info(short_name)
      tm.assert_series_equal(row_next_run, row_after)


if __name__ == '__main__':
  unittest.main()

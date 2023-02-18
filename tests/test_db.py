import copy
import string
import unittest
import os
import random
from math import sqrt
import pandas as pd
from pandas import testing as tm
from ae_rater_model import DBAccess, RatingCompetition
from ae_rater_types import MatchInfo, Outcome, ProfileInfo
from prioritizers import PrioritizerType
from rating_backends import ELO, Glicko

from src.metadata import ManualMetadata, get_metadata
from src.db_managers import MetadataManager
from src.helpers import short_fname
import tests.helpers as hlp
from tests.helpers import BACKUP_INITIAL_FILE, MEDIA_FOLDER, METAFILE, generate_outcome


def defgettr(stars) -> dict:
  stars = int(stars)
  return {"elo":1200+stars, "glicko":1500+stars, "tst":stars*10}

def factorize(n:int) -> list[int]:
  for i in range(2, int(sqrt(n)+1)):
    if n%i == 0:
      return [i] + factorize(n//i)
  return [n]



class TestDBAccess(unittest.TestCase):
  def setUp(self):
    self.dba = DBAccess(
      MEDIA_FOLDER,
      refresh=False,
      prioritizer_type=PrioritizerType.DEFAULT,
      rat_systems=[Glicko(),ELO()],
      history_fname='tst_history.csv'
    )

  def tearDown(self):
    hlp.disk_cleanup()

  def test_match_generation(self):
    def all_unique(li):
      seen = list()
      return not any(i in seen or seen.append(i) for i in li)
    for i in range(2,10):
      participants = self.dba.get_next_match(i)
      self.assertTrue(all_unique(participants))

  def test_get_leaderboard(self):
    ldbrd = self.dba.get_leaderboard()
    mediafiles = hlp.get_initial_mediafiles()
    self.assertTrue(hlp.is_sorted(ldbrd))
    self.assertSetEqual({short_fname(p.fullname) for p in ldbrd}, set(mediafiles))

  def test_get_match_history(self):
    mock_history = []
    for _ in range(random.randint(4,21)):
      N = random.randint(2,10)
      participants = self.dba.get_next_match(N)
      outcome_str = string.ascii_lowercase[:N] + " "*random.randint(N//2,N)
      outcome_str = ''.join(random.sample(outcome_str, len(outcome_str)))
      mock_history.append(MatchInfo(participants, Outcome(outcome_str)))
    for match in mock_history:
      self.dba.save_match(match)
    self.assertListEqual(self.dba.get_match_history(), mock_history)

  def test_apply_opinions(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    for _ in range(20):
      n = random.randint(2, min(15,len(all_files)))
      participants = self.dba.get_next_match(n)
      metadata = [get_metadata(p.fullname) for p in participants]
      outcome = generate_outcome(n)
      opinions, _ = RatingCompetition().consume_match(MatchInfo(participants, outcome))
      self.dba.apply_opinions(participants, opinions)
      news = [self._get_leaderboard_line(p.fullname) for p in participants]
      new_metadata = [get_metadata(p.fullname) for p in participants]

      for old_p, old_meta, new_p, new_meta in zip(participants, metadata, news, new_metadata):
        dbg_info = '\n'.join(map(str, [old_p, old_meta, new_p, new_meta]))
        self.assertEqual(new_p.nmatches, old_p.nmatches+len(participants)-1, dbg_info)
        self.assertSetEqual(old_meta.tags, new_meta.tags, dbg_info)
        self.assertEqual(old_meta.awards, new_meta.awards, dbg_info)
        self.assertEqual(int(old_p.stars), old_meta.stars, dbg_info)
        self.assertEqual(int(new_p.stars), new_meta.stars, dbg_info)
        for ratsys in old_p.ratings.keys():
          old_rating = old_p.ratings[ratsys]
          new_rating = new_p.ratings[ratsys]
          self.assertLessEqual(new_rating.rd, old_rating.rd)
          self.assertGreaterEqual(new_rating.timestamp, old_rating.timestamp)

  def _get_leaderboard_line(self, fullname:str) -> ProfileInfo:
    ldbrd = self.dba.get_leaderboard()
    return next(p for p in ldbrd if p.fullname==fullname)

  def _test_meta_update_impl(self, usr_input:ManualMetadata):
    N = random.randint(2,10)
    testees = self.dba.get_next_match(N)
    hlp.backup_files([p.fullname for p in testees])
    model = RatingCompetition()
    opinions, _ = model.consume_match(MatchInfo(
      testees,
      Outcome(' '.join(string.ascii_letters[:N]))  # to achieve fractional stars
    ))
    self.dba.apply_opinions(testees, opinions)
    testees = [self._get_leaderboard_line(p.fullname) for p in testees]

    same_stars = [True]*(N//2) + [False]*(N-N//2)  # if curr stars are 2.4, input 2 shouldn't change it
    for prof, frac_int_test in zip(testees, same_stars):
      meta_before = get_metadata(prof.fullname)
      prof_meta = ManualMetadata.from_str(prof.tags, int(prof.stars), prof.awards)
      self.assertEqual(meta_before, prof_meta)
      if frac_int_test:
        usr_input.stars = meta_before.stars

      self.dba.update_meta(prof.fullname, usr_input)

      dbg_info = f"{short_fname(prof.fullname)} frac_int:{frac_int_test}"
      meta_after = get_metadata(prof.fullname)
      self.assertEqual(meta_after, usr_input, dbg_info)
      new_prof = self._get_leaderboard_line(prof.fullname)
      new_prof_meta = ManualMetadata.from_str(new_prof.tags, int(new_prof.stars), new_prof.awards)
      self.assertEqual(new_prof_meta, usr_input, dbg_info)

  def test_meta_update_0(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        stars = random.randint(0, 5),
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_1(self):
    self._test_meta_update_impl(ManualMetadata(
        stars = random.randint(0, 5),
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_2(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_3(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        stars = random.randint(0, 5),
    ))

  def test_search_results(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    assert len(all_files) > 9, "need more samples for this test"
    test_files = random.sample(all_files, 10)
    hlp.backup_files(test_files)
    for i,fullname in enumerate(test_files):
      searchable_meta = ManualMetadata(
        tags=[f"tag{i}", f"factors{'#'.join(map(str, factorize(i)))}"],
        stars=5-5*i//len(test_files),
        awards=[f"awa{i}"],
      )
      self.dba.update_meta(fullname, searchable_meta)

    def assert_searches(query, idxs, context=""):
      self.assertListEqual(
        self.dba.get_search_results(query),
        [
          self._get_leaderboard_line(test_files[i])
          for i in idxs
        ],
        context,
      )
    assert_searches("tag9 awa9", [9], "AND, with results")
    assert_searches("tag9 awa8", [], "AND, empty")
    assert_searches("tag9|awa6", [6,9], "OR")
    self.assertEqual(len(self.dba.get_search_results("-tag9")), len(all_files)-1)
    self.assertSetEqual(
      {p.fullname for p in self.dba.get_search_results("mp4")},
      {fname for fname in all_files if fname.lower().endswith(".mp4")},
      "search filenames"
    )
    assert_searches("factors2", [2,4,6,8])
    assert_searches("2#2", [4,8])
    assert_searches("#3", [6,9])
    assert_searches("2# -#3 -3#", [4,8], "AND NOT")
    assert_searches("3#|#3", [6,9], "OR")
    assert_searches("factors7 | 2#2 -2#2#", [4,7], "complex")


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
    given_metadata = ManualMetadata.from_str(row['tags'], int(row['stars']), row['awards'])
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

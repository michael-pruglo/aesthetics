import unittest
import os
import random

from src.helpers import short_fname
from metadata import get_metadata
from ae_rater_types import Outcome, ProfileInfo
from ae_rater_model import RatingCompetition
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER, SKIPLONG


def is_sorted(l:list[ProfileInfo]) -> bool:
  return all(l[i].stars >= l[i+1].stars for i in range(len(l)-1))


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)
    self.N = len(self.model.get_leaderboard())

  def tearDown(self):
    hlp.disk_cleanup()

  def _get_leaderboard_line(self, fullname:str) -> ProfileInfo:
    ldbrd = self.model.get_leaderboard()
    return next(p for p in ldbrd if p.fullname==fullname)

  def test_match_generation(self):
    for _ in range(15):
      participants = self.model.generate_match()
      self.assertNotEqual(participants[0], participants[1])
      self.assertListEqual(self.model.get_curr_match(), participants)

  def test_get_leaderboard(self):
    ldbrd = self.model.get_leaderboard()
    mediafiles = hlp.get_initial_mediafiles()
    self.assertTrue(is_sorted(ldbrd))
    self.assertSetEqual({short_fname(p.fullname) for p in ldbrd}, set(mediafiles))

  def test_boost_generic(self):
    p = self.model.generate_match()[0]
    profile_before = self._get_leaderboard_line(p.fullname)
    self.assertEqual(p, profile_before)
    hlp.backup_files([p.fullname])
    self.model.give_boost(short_fname(p.fullname))
    profile_after = self._get_leaderboard_line(p.fullname)
    self.assertEqual(profile_after.tags, profile_after.tags)
    self.assertEqual(profile_before.nmatches, profile_after.nmatches)
    self.assertLessEqual(profile_before.stars, profile_after.stars)
    self.assertTrue(all(profile_before.ratings[s].points < profile_after.ratings[s].points
                        for s in profile_before.ratings.keys()))

  def test_boost_starchange(self):
    hlp.backup_files([os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()])
    for times in range(3):
      prof = self.model.generate_match()[0]
      stars_before = prof.stars
      for iter in range(25):
        self.model.give_boost(short_fname(prof.fullname))
        curr_stars_opinions = [s.get_boost(prof).new_stars for s in self.model.rat_systems]
        self.assertTrue(all(stars_before<=n<=5 for n in curr_stars_opinions), curr_stars_opinions)
        consensus_stars = min(curr_stars_opinions)
        profile_after = self._get_leaderboard_line(prof.fullname)
        dbg_info = f"curr profile: {prof},  profile_aftter: {profile_after}, opinions:{curr_stars_opinions}"
        if consensus_stars != stars_before:
          self.assertEqual(profile_after.stars, consensus_stars, dbg_info)
          self.assertEqual(consensus_stars, stars_before+1, dbg_info)
          _, disk_stars = get_metadata(prof.fullname)
          self.assertEqual(disk_stars, consensus_stars, dbg_info)
          break
        else:
          self.assertEqual(profile_after.stars, stars_before, dbg_info)
        prof = profile_after

  def test_matches_affect_disk(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    for _ in range(100):
      l, r = self.model.generate_match()
      l_tags, l_stars = get_metadata(l.fullname)
      r_tags, r_stars = get_metadata(r.fullname)
      outcome = random.choice([Outcome.WIN_LEFT, Outcome.DRAW, Outcome.WIN_RIGHT])
      self.model.consume_result(outcome)
      new_l = self._get_leaderboard_line(l.fullname)
      new_r = self._get_leaderboard_line(r.fullname)
      new_l_tags, new_l_stars = get_metadata(l.fullname)
      new_r_tags, new_r_stars = get_metadata(r.fullname)

      dbg_info = f"\n{l} {r}\n{new_l} {new_r}\n {outcome}"
      self.assertEqual(new_l.nmatches, l.nmatches+1, dbg_info)
      self.assertEqual(new_r.nmatches, r.nmatches+1, dbg_info)
      self.assertEqual(len(self.model.get_curr_match()), 0, dbg_info)
      self.assertEqual(l_tags, new_l_tags)
      self.assertEqual(r_tags, new_r_tags)
      self.assertEqual(l_stars, l.stars)
      self.assertEqual(r_stars, r.stars)
      self.assertEqual(new_l_stars, new_l.stars)
      self.assertEqual(new_r_stars, new_r.stars)
      self.assertTrue(all(l.ratings[s].rd >= new_l.ratings[s].rd for s in l.ratings.keys() if l.ratings[s].rd))
      self.assertTrue(all(r.ratings[s].rd >= new_r.ratings[s].rd for s in r.ratings.keys() if r.ratings[s].rd))
      self.assertTrue(all(l.ratings[s].timestamp < new_l.ratings[s].timestamp for s in l.ratings.keys()))
      self.assertTrue(all(r.ratings[s].timestamp < new_r.ratings[s].timestamp for s in r.ratings.keys()))

  @unittest.skipIf(*SKIPLONG)
  def test_long_term(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    loss = LongTermTester(self.model, verbosity=1).run()
    self.assertLess(loss, 0.9)


class LongTermTester:
  def __init__(self, model:RatingCompetition, verbosity=0):
    self.model = model
    self.verbosity = verbosity
    ldbrd = model.get_leaderboard()
    ranks = list(range(len(ldbrd)))
    random.shuffle(ranks)
    self.true_leaderboard = {p.fullname:rank for p,rank in zip(ldbrd,ranks)}

  def run(self, epochs=5) -> float:
    if self.verbosity: print()
    for epoch in range(epochs):
      for _ in range(500):
        l, r = self.model.generate_match()
        self.model.consume_result(self._simulate_outcome(l,r))
      if self.verbosity: print(f"{epoch}: loss = {self._loss()}")
      if self.verbosity>1: print("\n\n\n")

    return self._loss()

  def _simulate_outcome(self, l:ProfileInfo, r:ProfileInfo) -> Outcome:
      lrank = self.true_leaderboard[l.fullname]
      rrank = self.true_leaderboard[r.fullname]
      if lrank - rrank > 2:
        return Outcome.WIN_RIGHT
      if lrank - rrank < -2:
        return Outcome.WIN_LEFT
      return Outcome.DRAW

  def _loss(self) -> float:
    sq_err = 0
    ldbrd = self.model.get_leaderboard()
    for given_rating, p in enumerate(ldbrd):
      expected_rating = self.true_leaderboard[p.fullname]
      if self.verbosity>1: print(p, expected_rating)
      sq_err += (expected_rating-given_rating)**2
    return sq_err / len(ldbrd)


if __name__ == '__main__':
  unittest.main()

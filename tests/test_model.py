from cProfile import Profile
import unittest
import os
import random

from src.helpers import short_fname
from src.metadata import get_metadata
from src.ae_rater_types import Outcome, ProfileInfo
from src.ae_rater_model import RatingCompetition
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
    self.assertTrue(all(profile_before.ratings[s] < profile_after.ratings[s]
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

  def _simulate_match(self, lidx:int, ridx:int, outcome:Outcome, real_change:Outcome) -> tuple:
    ldbrd = self.model.get_leaderboard()
    l = self._get_leaderboard_line(ldbrd[lidx].fullname)
    r = self._get_leaderboard_line(ldbrd[ridx].fullname)
    l_tags, l_stars = get_metadata(l.fullname)
    r_tags, r_stars = get_metadata(r.fullname)
    self.model.curr_match = [l, r]
    self.model.consume_result(outcome)
    new_l = self._get_leaderboard_line(l.fullname)
    new_r = self._get_leaderboard_line(r.fullname)
    new_l_tags, new_l_stars = get_metadata(l.fullname)
    new_r_tags, new_r_stars = get_metadata(r.fullname)

    dbg_info = f"\n{l} {r}\n{new_l} {new_r}\n {outcome}\n {real_change}"
    self.assertEqual(new_l.nmatches, l.nmatches+1, dbg_info)
    self.assertEqual(new_r.nmatches, r.nmatches+1, dbg_info)
    self.assertEqual(len(self.model.get_curr_match()), 0, dbg_info)
    self.assertEqual(l_tags, new_l_tags)
    self.assertEqual(r_tags, new_r_tags)
    self.assertEqual(new_l_stars, new_l.stars)
    self.assertEqual(new_r_stars, new_r.stars)

    if real_change == Outcome.DRAW:
      self.assertFalse(new_l.stronger_than(l), dbg_info)
      self.assertFalse(l.stronger_than(new_l), dbg_info)
      self.assertFalse(new_r.stronger_than(r), dbg_info)
      self.assertFalse(r.stronger_than(new_r), dbg_info)
    elif real_change == Outcome.WIN_LEFT:
      self.assertTrue(new_l.stronger_than(l), dbg_info)
      self.assertTrue(r.stronger_than(new_r), dbg_info)
    elif real_change == Outcome.WIN_RIGHT:
      self.assertTrue(new_r.stronger_than(r), dbg_info)
      self.assertTrue(l.stronger_than(new_l), dbg_info)

    return l, r, new_l, new_r

  def _backup_by_idx(self, indexes:list[int]):
    ldbrd = self.model.get_leaderboard()
    hlp.backup_files([ldbrd[i].fullname for i in indexes])

  def test_revenge_match(self):
    ldbrd = self.model.get_leaderboard()
    while True:
      avenger = random.randint(1, self.N-3)
      if ldbrd[avenger].stars > 0:
        break
    bully = random.randint(max(0,avenger-5), avenger-1)
    self._backup_by_idx([bully, avenger])

    # right has the lowest rating for its stars and loses minimally
    l, r, new_l, new_r = self._simulate_match(bully, avenger, Outcome.WIN_LEFT, Outcome.WIN_LEFT)
    bully_initial, avenger_initial = l.ratings, r.ratings
    self.assertGreaterEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars-1)

    # revenge of the right, it gets back more than initial rating
    # while left drops even less than initial ratingcome.WIN_RIGHT))
    l, r, new_l, new_r = self._simulate_match(bully, avenger, Outcome.WIN_RIGHT, Outcome.WIN_RIGHT)
    self.assertEqual(new_l.stars, l.stars-1)
    self.assertEqual(new_r.stars, r.stars+1)
    self.assertTrue(all(new_l.ratings[s]<bully_initial[s] for s in new_l.ratings.keys()))
    self.assertTrue(all(new_r.ratings[s]>avenger_initial[s] for s in new_r.ratings.keys()))

  def test_draw_between_equals(self):
    ldbrd = self.model.get_leaderboard()
    equals_with_next = [i for i in range(self.N-1) if ldbrd[i].ratings==ldbrd[i+1].ratings]
    assert equals_with_next

    idx = random.choice(equals_with_next)
    self._backup_by_idx([idx, idx+1])
    l, r, new_l, new_r = self._simulate_match(idx, idx+1, Outcome.DRAW, Outcome.DRAW)
    self.assertEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars)

  def test_weak_draws_good_as_if_won(self):
    good = random.randint(0, self.N//3)
    weak = random.randint(self.N//3*2, self.N-1)
    self._backup_by_idx([good, weak])
    l, r, new_l, new_r = self._simulate_match(weak, good, Outcome.DRAW, Outcome.WIN_LEFT)
    self.assertGreaterEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars-1)

  def test_superexpected_win(self):
    supertop = random.randint(0,1)
    superweak = random.randint(self.N-2, self.N-1)
    self._backup_by_idx([supertop, superweak])
    l, r, new_l, new_r = self._simulate_match(superweak, supertop, Outcome.WIN_RIGHT, Outcome.DRAW)
    self.assertEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars)

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

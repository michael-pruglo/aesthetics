import unittest
import os
import random

from src.helpers import short_fname
from src.metadata import get_metadata
from src.ae_rater_types import Outcome, ProfileInfo
from src.ae_rater_model import RatingCompetition
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER


def is_sorted(l:list[ProfileInfo]) -> bool:
  return all(l[i].stars >= l[i+1].stars for i in range(len(l)-1))


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)

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
    for times in range(15):
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

  def test_match_outcomes(self):
    ldbrd = self.model.get_leaderboard()

    def prepare_schedule() -> list[tuple]:
      schedule:list[tuple] = []

      # first match: draw between identical ratings
      for _ in range(1000):  # near-infinite, bc there can be no identical stars
        l = random.randint(2, len(ldbrd)-2)
        if ldbrd[l+1].stars == ldbrd[l].stars:
          schedule.append((l, l+1, Outcome.DRAW, Outcome.DRAW))
          break
        if ldbrd[l-1].stars == ldbrd[l].stars:
          schedule.append((l, l-1, Outcome.DRAW, Outcome.DRAW))
          break

      # next matches
      topish = random.randint(3, len(ldbrd)//2)
      stronger = topish-2
      schedule.append((topish, stronger, Outcome.WIN_LEFT, Outcome.WIN_LEFT))
      weak = random.randint(len(ldbrd)//2+1, len(ldbrd)-2)
      schedule.append((topish, weak, Outcome.WIN_RIGHT, Outcome.WIN_RIGHT))

      schedule.append((0, len(ldbrd)-1, Outcome.WIN_LEFT, Outcome.DRAW))
      schedule.append((0, len(ldbrd)-1, Outcome.DRAW, Outcome.WIN_RIGHT))

      return schedule

    schedule = prepare_schedule()
    idxs = set()
    for l,r,*_ in schedule:
      idxs.update([l,r])
    hlp.backup_files(ldbrd[i].fullname for i in idxs)

    def simulate_match(lidx:int, ridx:int, outcome:Outcome, real_change:Outcome) -> tuple:
      l = self._get_leaderboard_line(ldbrd[lidx].fullname)
      r = self._get_leaderboard_line(ldbrd[ridx].fullname)
      self.model.curr_match = [l, r]
      self.model.consume_result(outcome)
      new_l = self._get_leaderboard_line(l.fullname)
      new_r = self._get_leaderboard_line(r.fullname)

      dbg_info = f"\n{l} {r}\n{new_l} {new_r}\n {outcome}\n {real_change}"
      self.assertEqual(new_l.nmatches, l.nmatches+1, dbg_info)
      self.assertEqual(new_r.nmatches, r.nmatches+1, dbg_info)
      self.assertEqual(len(self.model.get_curr_match()), 0, dbg_info)

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

    # draw between identical profiles
    l, r, new_l, new_r = simulate_match(*schedule[0])
    self.assertEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars)

    # right has the lowest rating for its stars and loses
    l, r, new_l, new_r = simulate_match(*schedule[1])
    self.assertGreaterEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars-1)

    # left (top half) loses to weak right (bottom half) and loses a star
    l, r, new_l, new_r = simulate_match(*schedule[2])
    self.assertEqual(new_l.stars, l.stars-1)
    self.assertGreaterEqual(new_r.stars, r.stars)

    # super expected win of the best over the worst
    l, r, new_l, new_r = simulate_match(*schedule[3])
    self.assertEqual(new_l.stars, l.stars)
    self.assertEqual(new_r.stars, r.stars)

    # shocking win of the worst over the best
    l, r, new_l, new_r = simulate_match(*schedule[4])
    self.assertEqual(new_l.stars, l.stars-1)
    self.assertGreaterEqual(new_r.stars, r.stars)


if __name__ == '__main__':
  unittest.main()

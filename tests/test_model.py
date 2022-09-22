import unittest
import os

from src.helpers import short_fname
from src.metadata import get_metadata
from src.ae_rater_types import ProfileInfo
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


if __name__ == '__main__':
  unittest.main()

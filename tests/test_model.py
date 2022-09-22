import unittest
import os

from src.helpers import short_fname
from src.ae_rater_types import ProfileInfo
from src.ae_rater_model import RatingCompetition
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER, METAFILE


def is_sorted(l:list[ProfileInfo]) -> bool:
  return all(l[i].stars >= l[i+1].stars for i in range(len(l)-1))


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)

  def tearDown(self):
    if os.path.exists(METAFILE):
      os.remove(METAFILE)

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

  def test_boost(self):
    participants = self.model.generate_match()
    fullname = participants[0].fullname
    profile_before = self._get_leaderboard_line(fullname)
    hlp.backup_files([fullname])
    self.model.give_boost(short_fname(fullname))
    profile_after = self._get_leaderboard_line(fullname)
    self.assertEqual(profile_after.tags, profile_after.tags)
    self.assertEqual(profile_before.nmatches, profile_after.nmatches)
    self.assertLessEqual(profile_before.stars, profile_after.stars)
    self.assertTrue(all(profile_before.ratings[s] < profile_after.ratings[s]
                        for s in profile_before.ratings.keys()))


if __name__ == '__main__':
  unittest.main()

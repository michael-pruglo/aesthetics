import unittest
import os

from src.helpers import short_fname
from src.ae_rater_types import ProfileInfo
from src.ae_rater_model import RatingCompetition
from tests.helpers import MEDIA_FOLDER, METAFILE, get_initial_mediafiles


def is_sorted(l:list[ProfileInfo]) -> bool:
  return all(l[i].stars >= l[i+1].stars for i in range(len(l)-1))


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)

  def tearDown(self):
    if os.path.exists(METAFILE):
      os.remove(METAFILE)

  def test_match_generation(self):
    for _ in range(15):
      participants = self.model.generate_match()
      self.assertNotEqual(participants[0], participants[1])

  def test_get_leaderboard(self):
    ldbrd = self.model.get_leaderboard()
    mediafiles = get_initial_mediafiles()
    self.assertTrue(is_sorted(ldbrd))
    self.assertSetEqual({short_fname(p.fullname) for p in ldbrd}, set(mediafiles))


if __name__ == '__main__':
  unittest.main()

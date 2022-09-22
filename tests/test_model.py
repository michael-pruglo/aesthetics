import unittest
import os

from src.ae_rater_model import RatingCompetition
from tests import MEDIA_FOLDER, METAFILE


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)

  def tearDown(self):
    if os.path.exists(METAFILE):
      os.remove(METAFILE)

  def test_match_generation(self):
    for _ in range(15):
      participants = self.model.generate_match()
      self.assertEqual(len(participants), 2)
      self.assertNotEqual(participants[0], participants[1])


if __name__ == '__main__':
  unittest.main()

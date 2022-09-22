import unittest

from src.ae_rater_model import RatingCompetition
from tests import MEDIA_FOLDER


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)

  def test_match_generation(self):
    pass


if __name__ == '__main__':
  unittest.main()

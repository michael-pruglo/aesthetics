import random
import unittest

from src.rating_backends import RatingBackend, ELO
from src.ae_rater_types import ProfileInfo


class TestRatingSystem(unittest.TestCase):
  def _test_system(self, system:RatingBackend):
    self._test_stars_rating_conversion(system)
    self._test_boost(system)

  def _test_boost(self, system:RatingBackend):
    self._test_random_boosts(system)
    self._test_boost_updates_stars(system)
    self._test_boost_caps_at_5_stars(system)

  def _test_random_boosts(self, system):
    for _ in range(50):
      rating = random.randint(0, 3000)
      prof = ProfileInfo("","", system.rating_to_stars(rating),
                         {system.name():rating}, random.randint(0,2000))
      change = system.get_boost(prof)
      self.assertGreater(change.delta_rating, 0)
      self.assertEqual(change.new_rating, rating+change.delta_rating)
      self.assertGreaterEqual(change.new_stars, prof.stars)
      self.assertEqual(change.new_stars, system.rating_to_stars(change.new_rating))

  def _test_boost_updates_stars(self, system):
    for s in range(1,6):
      rating = system.stars_to_rating(s) - 1
      prof = ProfileInfo("","",s-1,{system.name():rating},random.randint(0,2000))
      change = system.get_boost(prof)
      self.assertEqual(change.new_stars, s)

  def _test_boost_caps_at_5_stars(self, system):
    rating = system.stars_to_rating(5)
    prof = ProfileInfo("","",5,{system.name():rating},random.randint(0,2000))
    for _ in range(300):
      change = system.get_boost(prof)
      self.assertEqual(change.new_stars, 5)
      self.assertGreater(change.new_rating, prof.ratings[system.name()])
      prof.stars = change.new_stars
      prof.ratings[system.name()] = change.new_rating

  def _test_stars_rating_conversion(self, system:RatingBackend):
    curr_stars = 0
    for rat in range(10,3000,20):
      new_stars = system.rating_to_stars(rat)
      self.assertTrue(0 <= new_stars <= 5)
      self.assertTrue(new_stars >= curr_stars)
      curr_stars = new_stars

    for s in range(0,6):
      self.assertEqual(system.rating_to_stars(system.stars_to_rating(s)), s)


  def test_elo(self):
    self._test_system(ELO())

  def test_glicko(self):
    pass

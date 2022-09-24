import unittest
import random
import copy
import numpy as np

from rating_backends import RatingBackend, ELO
from ae_rater_types import ProfileInfo, RatChange, Outcome


def construct_profile(system:RatingBackend, rating:int=None, stars:int=None):
  if rating is None:
    rating = random.randint(0,3000)
  if stars is None:
    stars = system.rating_to_stars(rating)
  return ProfileInfo("generic tags", "generic name", stars,
                      {system.name():rating}, random.randint(0,2000))


class TestRatingSystem(unittest.TestCase):
  def _test_system(self, system:RatingBackend):
    self._test_stars_rating_conversion(system)
    self._test_boost(system)
    self._test_matches(system)

  def _test_stars_rating_conversion(self, system:RatingBackend):
    curr_stars = 0
    for rat in range(10,3000,20):
      new_stars = system.rating_to_stars(rat)
      self.assertTrue(0 <= new_stars <= 5)
      self.assertTrue(new_stars >= curr_stars)
      curr_stars = new_stars

    for s in range(0,6):
      self.assertEqual(system.rating_to_stars(system.stars_to_rating(s)), s)

  def _test_boost(self, system:RatingBackend):
    self._test_random_boosts(system)
    self._test_boost_updates_stars(system)
    self._test_boost_caps_at_5_stars(system)

  def _test_random_boosts(self, system:RatingBackend):
    for _ in range(50):
      rating = random.randint(0, 3000)
      prof = construct_profile(system, rating)
      change = system.get_boost(prof)
      self.assertGreater(change.delta_rating, 0)
      self.assertEqual(change.new_rating, rating+change.delta_rating)
      self.assertGreaterEqual(change.new_stars, prof.stars)
      self.assertEqual(change.new_stars, system.rating_to_stars(change.new_rating))

  def _test_boost_updates_stars(self, system:RatingBackend):
    for s in range(1,6):
      rating = system.stars_to_rating(s) - 1
      prof = construct_profile(system, rating, s-1)
      change = system.get_boost(prof)
      self.assertEqual(change.new_stars, s)

  def _test_boost_caps_at_5_stars(self, system:RatingBackend):
    rating = system.stars_to_rating(5)
    prof = construct_profile(system, rating, 5)
    for _ in range(300):
      change = system.get_boost(prof)
      self.assertEqual(change.new_stars, 5)
      self.assertGreater(change.new_rating, prof.ratings[system.name()])
      prof.stars = change.new_stars
      prof.ratings[system.name()] = change.new_rating

  def _test_matches(self, system:RatingBackend):
    a = b = construct_profile(system)
    changes = system.process_match(a, b, Outcome.DRAW)
    self.assertEqual(changes[0], RatChange(a.ratings[system.name()], 0, a.stars))
    self.assertEqual(changes[1], RatChange(b.ratings[system.name()], 0, b.stars))
    changes = system.process_match(a, b, Outcome.WIN_LEFT)
    self.assertGreater(changes[0].delta_rating, 0)
    self.assertLess(changes[1].delta_rating, 0)
    changes = system.process_match(a, b, Outcome.WIN_RIGHT)
    self.assertLess(changes[0].delta_rating, 0)
    self.assertGreater(changes[1].delta_rating, 0)

    a = construct_profile(system, 0)
    b = copy.deepcopy(a)
    for outcome in [Outcome.DRAW, Outcome.WIN_LEFT, Outcome.WIN_RIGHT]:
      gaps, a_deltas, b_deltas = [], [], []
      for gap in range(5,2000,50):
        b.ratings[system.name()] = a.ratings[system.name()]+gap
        ch = system.process_match(a, b, outcome)
        gaps.append(b.ratings[system.name()])
        a_deltas.append(ch[0].delta_rating)
        b_deltas.append(ch[1].delta_rating)

      a_slope = np.polyfit(gaps, a_deltas, deg=1)[0]
      b_slope = np.polyfit(gaps, b_deltas, deg=1)[0]
      self.assertGreater(a_slope, 0)
      self.assertLess(b_slope, 0)


  def test_elo(self):
    self._test_system(ELO())

  def test_glicko(self):
    pass


if __name__ == "__main__":
  unittest.main()

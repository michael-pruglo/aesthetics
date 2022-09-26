import unittest
import random
import copy
import numpy as np

from rating_backends import RatingBackend, ELO, Glicko
from ae_rater_types import ProfileInfo, Outcome, Rating

def make_testcase(system:RatingBackend):
  sname = system.name()


  def construct_profile(rating:Rating=None, stars:int=None, matches:int=None):
    if rating is None:
      rating = Rating(random.randint(0,3000), random.randint(30,300))
    if stars is None:
      stars = system.rating_to_stars(rating)
    if matches is None:
      matches = random.randint(0, 2000)
    return ProfileInfo("autotgs", "autonm", stars, {system.name():rating}, matches)


  class TestRatingSystemImpl(unittest.TestCase):
    def test_stars_rating_conversion(self):
      curr_stars = 0
      for pts in range(10,3000,20):
        rat = Rating(pts)
        new_stars = system.rating_to_stars(rat)
        self.assertTrue(0 <= new_stars <= 5)
        self.assertTrue(new_stars >= curr_stars)
        curr_stars = new_stars

      for s in range(0,6):
        self.assertEqual(system.rating_to_stars(system.stars_to_rating(s)), s)

    def test_random_boosts(self):
      for _ in range(50):
        rating = Rating(random.randint(0, 3000), random.randint(30,300))
        prof = construct_profile(rating)
        change = system.get_boost(prof)
        self.assertGreater(change.delta_rating, 0)
        self.assertEqual(change.new_rating.points, rating.points+change.delta_rating)
        self.assertGreaterEqual(change.new_stars, prof.stars)
        self.assertEqual(change.new_stars, system.rating_to_stars(change.new_rating))

    def test_boost_updates_stars(self):
      for s in range(1,6):
        rating = Rating(system.stars_to_rating(s).points-1, random.randint(30,300))
        prof = construct_profile(rating, s-1)
        change = system.get_boost(prof)
        self.assertEqual(change.new_stars, s)

    def test_boost_caps_at_5_stars(self):
      rating = system.stars_to_rating(5)
      prof = construct_profile(rating, 5)
      for _ in range(300):
        change = system.get_boost(prof)
        self.assertEqual(change.new_stars, 5)
        self.assertGreater(change.new_rating.points, prof.ratings[sname].points)
        prof.stars = change.new_stars
        prof.ratings[sname] = change.new_rating

    def test_matches_basic(self):
      a = b = construct_profile()
      changes = system.process_match(a, b, Outcome.DRAW)
      for i, prof in zip([0,1], [a,b]):
        self.assertEqual(changes[i].new_rating.points, prof.ratings[sname].points)
        self.assertEqual(changes[i].delta_rating, 0)
        self.assertEqual(changes[i].new_stars, prof.stars)
        self.assertLessEqual(changes[i].new_rating.rd, prof.ratings[sname].rd)
        self.assertGreaterEqual(changes[i].new_rating.timestamp, prof.ratings[sname].timestamp)

      changes = system.process_match(a, b, Outcome.WIN_LEFT)
      self.assertGreater(changes[0].delta_rating, 0)
      self.assertLess(changes[1].delta_rating, 0)
      for i, prof in zip([0,1], [a,b]):
        self.assertLessEqual(changes[i].new_rating.rd, prof.ratings[sname].rd)
        self.assertGreaterEqual(changes[i].new_rating.timestamp, prof.ratings[sname].timestamp)

      changes = system.process_match(a, b, Outcome.WIN_RIGHT)
      self.assertLess(changes[0].delta_rating, 0)
      self.assertGreater(changes[1].delta_rating, 0)
      for i, prof in zip([0,1], [a,b]):
        self.assertLessEqual(changes[i].new_rating.rd, prof.ratings[sname].rd)
        self.assertGreaterEqual(changes[i].new_rating.timestamp, prof.ratings[sname].timestamp)

    def test_matches_gap_dependency(self):
      a = construct_profile(Rating(0, random.randint(30,300)))
      b = copy.deepcopy(a)
      for outcome in [Outcome.DRAW, Outcome.WIN_LEFT, Outcome.WIN_RIGHT]:
        gaps, a_deltas, b_deltas = [], [], []
        for gap in range(5,2000,50):
          b.ratings[sname].points = a.ratings[sname].points + gap
          ch = system.process_match(a, b, outcome)
          gaps.append(b.ratings[sname].points)
          a_deltas.append(ch[0].delta_rating)
          b_deltas.append(ch[1].delta_rating)

        a_slope = np.polyfit(gaps, a_deltas, deg=1)[0]
        b_slope = np.polyfit(gaps, b_deltas, deg=1)[0]
        self.assertGreater(a_slope, 0)
        self.assertLess(b_slope, 0)

    def test_scenario_revenge(self):
      bully0_stars = random.randint(3,5)
      avenger0_stars = bully0_stars - random.randint(0,2)
      matches = random.randint(0, 100)
      bully0 = construct_profile(system.stars_to_rating(bully0_stars), bully0_stars, matches)
      avenger0 = construct_profile(system.stars_to_rating(avenger0_stars), avenger0_stars, matches)

      ch_bully1, ch_avenger1 = system.process_match(bully0, avenger0, Outcome.WIN_LEFT)
      bully1 = construct_profile(ch_bully1.new_rating, ch_bully1.new_stars, matches)
      avenger1 = construct_profile(ch_avenger1.new_rating, ch_avenger1.new_stars, matches)
      self.assertGreaterEqual(ch_bully1.new_stars, bully0.stars)
      self.assertGreater(ch_bully1.delta_rating, 0)
      self.assertGreater(ch_bully1.new_rating, bully0.ratings[sname])
      self.assertLess(ch_avenger1.new_stars, avenger0.stars)
      self.assertLess(ch_avenger1.delta_rating, 0)
      self.assertLess(ch_avenger1.new_rating, avenger0.ratings[sname])
      self.assertLessEqual(ch_avenger1.new_rating.rd, avenger0.ratings[sname].rd)
      self.assertGreater(ch_avenger1.new_rating.timestamp, avenger0.ratings[sname].timestamp)

      ch_bully2, ch_avenger2 = system.process_match(bully1, avenger1, Outcome.WIN_RIGHT)
      self.assertLess(ch_bully2.new_stars, bully1.stars)
      self.assertLess(ch_bully2.delta_rating, 0)
      self.assertLess(ch_bully2.new_rating, bully0.ratings[sname])
      self.assertGreater(ch_avenger2.new_stars, avenger1.stars)
      self.assertGreater(ch_avenger2.delta_rating, 0)
      self.assertGreater(ch_avenger2.new_rating, avenger0.ratings[sname])
      self.assertLessEqual(ch_avenger2.new_rating.rd, avenger1.ratings[sname].rd)
      self.assertGreater(ch_avenger2.new_rating.timestamp, avenger1.ratings[sname].timestamp)

    def test_scenario_draw_between_equals(self):
      p = construct_profile()
      ch1, ch2 = system.process_match(p, p, Outcome.DRAW)
      self.assertEqual(ch1, ch2)
      self.assertEqual(ch1.new_stars, p.stars)
      self.assertEqual(ch1.new_rating.points, p.ratings[sname].points)
      self.assertLessEqual(ch1.new_rating.rd, p.ratings[sname].rd)
      self.assertGreater(ch1.new_rating.timestamp, p.ratings[sname].timestamp)

    def test_scenario_weak_draws_strong_as_if_won(self):
      weak = construct_profile(system.stars_to_rating(0), 0)
      strong = construct_profile(system.stars_to_rating(5), 5)
      weak.ratings[sname].rd = strong.ratings[sname].rd = 90
      ch_weak, ch_strong = system.process_match(weak, strong, Outcome.DRAW)
      self.assertLess(ch_strong.delta_rating, 0)
      self.assertLessEqual(ch_strong.new_stars, strong.stars)
      self.assertLess(ch_strong.new_rating.points, strong.ratings[sname].points)
      self.assertLessEqual(ch_strong.new_rating.rd, strong.ratings[sname].rd)
      self.assertGreater(ch_strong.new_rating.timestamp, strong.ratings[sname].timestamp)

      self.assertGreater(ch_weak.delta_rating, 0)
      self.assertGreaterEqual(ch_weak.new_stars, weak.stars)
      self.assertGreater(ch_weak.new_rating.points, weak.ratings[sname].points)
      self.assertLessEqual(ch_weak.new_rating.rd, weak.ratings[sname].rd)
      self.assertGreater(ch_weak.new_rating.timestamp, weak.ratings[sname].timestamp)

    def test_scenario_superexpected_win(self):
      weak = construct_profile(system.stars_to_rating(0), 0)
      strong = construct_profile(system.stars_to_rating(5), 5)
      weak.ratings[sname].rd = strong.ratings[sname].rd = 90
      ch_weak, ch_strong = system.process_match(weak, strong, Outcome.WIN_RIGHT)
      self.assertEqual(ch_strong.delta_rating, 0)
      self.assertEqual(ch_strong.new_stars, strong.stars)
      self.assertEqual(ch_strong.new_rating.points, strong.ratings[sname].points)
      self.assertLessEqual(ch_strong.new_rating.rd, strong.ratings[sname].rd)
      self.assertGreater(ch_strong.new_rating.timestamp, strong.ratings[sname].timestamp)

      self.assertEqual(ch_weak.delta_rating, 0)
      self.assertEqual(ch_weak.new_stars, weak.stars)
      self.assertEqual(ch_weak.new_rating.points, weak.ratings[sname].points)
      self.assertLessEqual(ch_weak.new_rating.rd, weak.ratings[sname].rd)
      self.assertGreater(ch_weak.new_rating.timestamp, weak.ratings[sname].timestamp)


  return TestRatingSystemImpl


class TestELO(make_testcase(ELO())):
  pass

class TestGlicko(make_testcase(Glicko())):
  pass


if __name__ == "__main__":
  unittest.main()

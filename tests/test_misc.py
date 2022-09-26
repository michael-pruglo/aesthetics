import unittest

from ae_rater_types import ProfileInfo, Rating


class TestTypes(unittest.TestCase):
  def test_profile_comparison(self):
    def compare(better:ProfileInfo, worse:ProfileInfo):
      dbg_info = f"\nbetter:{better}\n worse:{worse}"
      self.assertTrue(better.stronger_than(worse), dbg_info)
      self.assertFalse(worse.stronger_than(better), dbg_info)

    a = ProfileInfo("","",2,{'elo':Rating(1200),'glicko':Rating(1500,42)},123)
    b = ProfileInfo("","",3,{'elo':Rating(1400),'glicko':Rating(1700,27)},23)
    c = ProfileInfo("","",2,{'elo':Rating(1201),'glicko':Rating(1500,12)},3)

    compare(b, a)
    compare(c, a)
    compare(b, c)

  def test_rating_comparison(self):
    self.assertTrue(Rating(1000, 100, 0) == Rating(1000, 100, 8))
    self.assertTrue(Rating(1000, 100, 0) < Rating(1000, 9, 0))
    self.assertTrue(Rating(999, 100, 0) < Rating(1000, 100, 0))
    self.assertTrue(Rating(333, 40, 0) > Rating(216, 100, 0))

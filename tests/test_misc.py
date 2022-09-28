import unittest

from ae_rater_types import Outcome, ProfileInfo, Rating


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

  def test_outcomes(self):
    self.assertDictEqual(
      Outcome("a b").as_dict(),
      {
        0: [(1,1)],
        1: [(0,0)],
      }
    )
    self.assertDictEqual(
      Outcome("b a").as_dict(),
      {
        1: [(0,1)],
        0: [(1,0)],
      }
    )
    self.assertDictEqual(
      Outcome("ab").as_dict(),
      {
        0: [(1,0.5)],
        1: [(0,0.5)],
      }
    )
    self.assertDictEqual(Outcome("ab").as_dict(), Outcome("ba").as_dict())
    self.assertDictEqual(
      Outcome("ab c def g h i").as_dict(),
      {
        0: [         (1,0.5), (2,1.0), (3,1.0), (4,1.0), (5,1.0), (6,1.0), (7,1.0), (8,1.0)],
        1: [(0,0.5),          (2,1.0), (3,1.0), (4,1.0), (5,1.0), (6,1.0), (7,1.0), (8,1.0)],
        2: [(0,0.0), (1,0.0),          (3,1.0), (4,1.0), (5,1.0), (6,1.0), (7,1.0), (8,1.0)],
        3: [(0,0.0), (1,0.0), (2,0.0),          (4,0.5), (5,0.5), (6,1.0), (7,1.0), (8,1.0)],
        4: [(0,0.0), (1,0.0), (2,0.0), (3,0.5),          (5,0.5), (6,1.0), (7,1.0), (8,1.0)],
        5: [(0,0.0), (1,0.0), (2,0.0), (3,0.5), (4,0.5),          (6,1.0), (7,1.0), (8,1.0)],
        6: [(0,0.0), (1,0.0), (2,0.0), (3,0.0), (4,0.0), (5,0.0),          (7,1.0), (8,1.0)],
        7: [(0,0.0), (1,0.0), (2,0.0), (3,0.0), (4,0.0), (5,0.0), (6,0.0),          (8,1.0)],
        8: [(0,0.0), (1,0.0), (2,0.0), (3,0.0), (4,0.0), (5,0.0), (6,0.0), (7,0.0),        ],
      }
    )

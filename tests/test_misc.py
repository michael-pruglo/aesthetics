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


class TestOucome(unittest.TestCase):
  def test_1v1(self):
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

  def test_multimatch(self):
    s = "a++b- c+-++-+ de-f+ g h i"

    self.assertTrue(Outcome.is_valid(s))
    for i in range(12):
      self.assertEqual(Outcome.is_valid(s,i), i==9)

    outcome = Outcome(s)
    self.assertDictEqual(outcome.get_boosts(), {
      0:2, 1:-1, 2:2, 4:-1, 5:1,
    })

    self.assertDictEqual(
      outcome.as_dict(),
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

  def test_invalid(self):
    valid = {
      "b+a-  ":2,
      "  d a-b-c+":4,
      "a+++++++++++++++++ b":2,
      "c+-++++-+-+----- b a":3,
      "b--------------- a":2,
      "de---+-+ abc":5,
    }
    for s, n in valid.items():
      self.assertTrue(Outcome.is_valid(s), s)
      for i in range(12):
        self.assertEqual(Outcome.is_valid(s, i), i==n, s)
        self.assertEqual(Outcome.is_valid(s, i, intermediate=True), i>=n, s)

    invalid = {
      "dc": "lacks 'a' and 'b'",
      "+ab": "'+' to no one",
      "-ab": "'-' to no one",
      "b + ca": "no spaces before '+' allowed",
      "b - ca": "no spaces before '-' allowed",
      "w a b": "'w' without predecesors",
      "a_b": "invalid symbol '_'",
    }
    for s, reason in invalid.items():
      self.assertFalse(Outcome.is_valid(s), reason)
      if s!="dc":
        for i in range(12):
          self.assertFalse(Outcome.is_valid(s, i, intermediate=True), reason)

    self.assertTrue(Outcome.is_valid(" d+c", 5, intermediate=True))
    self.assertFalse(Outcome.is_valid(" dc--", 3, intermediate=True))
    self.assertTrue(Outcome.is_valid("c++d- e f", 10, intermediate=True))

  def test_boosts(self):
    boosts = {
      "c a d b": {},
      "a efd b- c": {1:-1},
      "c++-ab": {2:1},
      "a+-": {},
      "e++-b+c d-- a+-++ f-g+": {0:2, 1:1, 3:-2, 4:1, 5:-1, 6:1},
    }
    for s, expected in boosts.items():
      self.assertDictEqual(Outcome(s).get_boosts(), expected, s)

  def test_intermediate_predictions(self):
    cases = {
      "d+-+ a+": ({3:0, 0:1}, 6, "predict these are leaders"),
      "cb++": ({2:0, 1:0}, 12, "predict these are leaders"),
      "ca+- f++ ": ({2:0, 0:0, 5:1}, 8, "predict these are leaders"),
      " f-a d": ({5:3, 0:3, 3:4}, 6, "whitespace in front means these are last"),
      " cf+ a-+b+ ": ({2:1, 5:1, 0:2, 1:2}, 6, "whitespace both sides means these are middle"),
    }
    for s, (exp_tiers, n, reason) in cases.items():
      tiers, max_tier = Outcome.predict_tiers_intermediate(s, n)
      self.assertDictEqual(tiers, exp_tiers, reason)
      self.assertTrue(len(exp_tiers) <= max_tier <= n, reason)


if __name__ == "__main__":
  unittest.main()

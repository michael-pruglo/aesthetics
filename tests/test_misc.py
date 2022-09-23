import unittest

from src.ae_rater_types import ProfileInfo


class TestTypes(unittest.TestCase):
  def test_profile_comparison(self):
    def compare(better:ProfileInfo, worse:ProfileInfo):
      dbg_info = f"\nbetter:{better}\n worse:{worse}"
      self.assertTrue(better.stronger_than(worse), dbg_info)
      self.assertFalse(worse.stronger_than(better), dbg_info)

    a = ProfileInfo("","",2,{'elo':1200,'glicko':1500},123)
    b = ProfileInfo("","",3,{'elo':1400,'glicko':1700},23)
    c = ProfileInfo("","",2,{'elo':1201,'glicko':1500},3)

    compare(b, a)
    compare(c, a)
    compare(b, c)

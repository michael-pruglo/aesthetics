import unittest
import os
import shutil

from metadata import *
from tests.helpers import MEDIA_FOLDER


class TestReadingMetadata(unittest.TestCase):
  def _test_metadata_read(self, short_name:str, exp_meta:ManualMetadata):
    fname = os.path.join(MEDIA_FOLDER, "fixed/"+short_name)
    self.assertTrue(os.path.exists(fname), fname)
    self.assertEqual(get_metadata(fname), exp_meta)

  def test_libxmp(self):
    self._test_metadata_read(
      "006f129e1d4baaa9cd5e766d06256f58.jpg",
      ManualMetadata(
         tags={"hair", "hair|front_locks", "face", "eyes", "eyes|eyelines"},
         stars=5,
         awards={'investigation', 'Further'},
      )
    )
    self._test_metadata_read("no_metadata.JPG", ManualMetadata())


class TestWritingMetadata(unittest.TestCase):
  def setUp(self):
    original = os.path.join(MEDIA_FOLDER, "fixed/no_metadata.JPG")
    self.assertTrue(os.path.exists(original), original)
    self.fname = os.path.join(MEDIA_FOLDER, "fixed/tmp_write.jpg")
    self.assertFalse(os.path.exists(self.fname), self.fname)
    shutil.copyfile(original, self.fname)
    self.assertTrue(os.path.exists(self.fname), self.fname)

  def tearDown(self):
    self.assertTrue(os.path.exists(self.fname), self.fname)
    os.remove(self.fname)
    self.assertFalse(os.path.exists(self.fname), self.fname)

  def test_sweep(self):
    for st in range(6):
      for tg in [set(), {"blah", "blah|hierarchical", "another"}, {"mood", "mood|smile", "color"}]:
        for aw in [set(), {"e_awa", "e_22"}, {"perfect", "daily"}]:
          meta = ManualMetadata(tg, st, aw)
          write_metadata(self.fname, meta)
          self.assertEqual(get_metadata(self.fname), meta)

  def test_overwrite(self):
    tgs1 = {"a", "b|_c", "b|_d", "b"}
    tgs2 = {"m", "m|n", "m|n|o", "p"}
    meta1 = ManualMetadata(tgs1, 4)
    meta2 = ManualMetadata(tgs2, 4)
    write_metadata(self.fname, meta1)
    self.assertEqual(get_metadata(self.fname), meta1)
    write_metadata(self.fname, meta2)
    self.assertEqual(get_metadata(self.fname), meta2)


if __name__ == '__main__':
  unittest.main()

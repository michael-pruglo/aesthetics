import unittest
import os
import shutil
from typing import Callable

from src.metadata import *


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")


class TestReadingMetadata(unittest.TestCase):
  def _test_metadata_read(self,
    short_name:str,
    getter,
    expected_rating:int,
    expected_tags:set[str]
  ):
    fname = os.path.join(MEDIA_FOLDER, "fixed/"+short_name)
    self.assertTrue(os.path.exists(fname), fname)
    tags, rating = getter(fname)
    self.assertEqual(rating, expected_rating)
    self.assertSetEqual(set(tags), expected_tags)

  def _test_metaread_function(self, getter:Callable[[str],tuple[list,int]]):
    self._test_metadata_read(
      "006f129e1d4baaa9cd5e766d06256f58.jpg", getter, 5,
      {"hair", "hair|front_locks", "face", "eyes", "eyes|eyelines"},
    )
    with self.assertRaises(RuntimeError):
      self._test_metadata_read("no_metadata.png", getter, 0, {})

  def test_libxmp(self):
    self._test_metaread_function(get_metadata)

  def test_pillow(self):
    self._test_metaread_function(get_metadata2)


class TestWritingMetadata(unittest.TestCase):
  def setUp(self):
    original = os.path.join(MEDIA_FOLDER, "fixed/no_metadata.png")
    self.assertTrue(os.path.exists(original), original)
    self.fname = os.path.join(MEDIA_FOLDER, "fixed/tmp_write.png")
    self.assertFalse(os.path.exists(self.fname), self.fname)
    shutil.copyfile(original, self.fname)
    self.assertTrue(os.path.exists(self.fname), self.fname)

  def tearDown(self) -> None:
    self.assertTrue(os.path.exists(self.fname), self.fname)
    os.remove(self.fname)
    self.assertFalse(os.path.exists(self.fname), self.fname)

  # def test_libxmp_writing_rating(self):
  # def test_libxmp_writing_tags(self):
  # def test_libxmp_writing_both(self):
  # def test_libxmp_writing_append(self):
  #   append = True and False
  #   pass


if __name__ == '__main__':
  unittest.main(verbosity=2)

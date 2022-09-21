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
    self.assertTupleEqual(getter(fname), (expected_tags, expected_rating))

  def _test_metaread_function(self, getter:Callable[[str],tuple[set[str],int]]):
    self._test_metadata_read(
      "006f129e1d4baaa9cd5e766d06256f58.jpg", getter, 5,
      {"hair", "hair|front_locks", "face", "eyes", "eyes|eyelines"},
    )
    self._test_metadata_read("no_metadata.JPG", getter, 0, set())

  def test_libxmp(self):
    self._test_metaread_function(get_metadata)

  def test_pillow(self):
    self._test_metaread_function(get_metadata2)


class TestWritingMetadata(unittest.TestCase):
  def setUp(self):
    original = os.path.join(MEDIA_FOLDER, "fixed/no_metadata.JPG")
    self.assertTrue(os.path.exists(original), original)
    self.fname = os.path.join(MEDIA_FOLDER, "fixed/tmp_write.jpg")
    self.assertFalse(os.path.exists(self.fname), self.fname)
    shutil.copyfile(original, self.fname)
    self.assertTrue(os.path.exists(self.fname), self.fname)

  def tearDown(self) -> None:
    self.assertTrue(os.path.exists(self.fname), self.fname)
    os.remove(self.fname)
    self.assertFalse(os.path.exists(self.fname), self.fname)

  def _test_writing(self, tags:set[str]=None, rating:int=None):
    write_metadata(self.fname, tags=tags, append=False, rating=rating)
    t, r = get_metadata(self.fname)
    self.assertSetEqual(t, tags or set())
    self.assertEqual(r, rating or 0)

  def test_writing_rating(self):
    self._test_writing(rating=3)

  def test_writing_tags(self):
    self._test_writing(tags={'blah', 'blah|hierarchical', 'another'})

  def test_writing_both(self):
    self._test_writing({"mood", "mood|smile", "color"}, 4)

  def test_writing_append(self):
    tgs = {"a","b|_c","b|_d","b"}
    rat = 3
    write_metadata(self.fname, tags=tgs, rating=rat)
    self.assertTupleEqual(get_metadata(self.fname), (tgs, rat))



if __name__ == '__main__':
  unittest.main()

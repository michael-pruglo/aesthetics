import unittest
import os
import shutil
from typing import Callable

from src.metadata import *
from tests.helpers import MEDIA_FOLDER


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

  def test_only_rating(self):
    write_metadata(self.fname, rating=3)
    self.assertTupleEqual(get_metadata(self.fname), (set(),3))

  def test_only_tags(self):
    tgs = {'blah', 'blah|hierarchical', 'another'}
    write_metadata(self.fname, tags=tgs)
    self.assertTupleEqual(get_metadata(self.fname), (tgs,0))

  def test_both(self):
    tgs = {"mood", "mood|smile", "color"}
    write_metadata(self.fname, tags=tgs, rating=1)
    self.assertTupleEqual(get_metadata(self.fname), (tgs,1))

  def test_append(self):
    tgs1 = {"a", "b|_c", "b|_d", "b"}
    tgs2 = {"m", "m|n", "m|n|o", "p"}
    write_metadata(self.fname, tags=tgs1, rating=4)
    self.assertTupleEqual(get_metadata(self.fname), (tgs1,4))
    write_metadata(self.fname, tags=tgs2, rating=1, append=True)
    self.assertTupleEqual(get_metadata(self.fname), (tgs1|tgs2, 1))

  def test_overwrite(self):
    tgs1 = {"a", "b|_c", "b|_d", "b"}
    tgs2 = {"m", "m|n", "m|n|o", "p"}
    write_metadata(self.fname, tags=tgs1, rating=4)
    self.assertTupleEqual(get_metadata(self.fname), (tgs1,4))
    write_metadata(self.fname, tags=tgs2, rating=1, append=False)
    self.assertTupleEqual(get_metadata(self.fname), (tgs2, 1))


if __name__ == '__main__':
  unittest.main()

import unittest
import os

from src.metadata import get_metadata
from src.db_managers import *


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")


class TestMetadataManager(unittest.TestCase):
  def setUp(self) -> None:
    assert os.path.exists(MEDIA_FOLDER)
    self.nfiles = len([f for f in os.listdir(MEDIA_FOLDER)
                       if os.path.isfile(os.path.join(MEDIA_FOLDER, f))
                       and f.split('.')[-1] != 'csv'])
    assert self.nfiles > 2

  def tearDown(self) -> None:
    db_file = os.path.join(MEDIA_FOLDER, "metadata_db.csv")
    if os.path.exists(db_file):
      os.remove(db_file)

  def test_init_fresh(self):
    mm = MetadataManager(MEDIA_FOLDER)
    db = mm.get_db()
    self.assertEqual(len(db), self.nfiles)
    self.assertTrue({'tags','stars','nmatches'}.issubset(db.columns))
    self.assertTrue((db['tags'].notna()).all())
    self.assertTrue((db['stars'].between(0,5)).all())
    self.assertTrue((db['nmatches']==0).all())
    for short_name, row in db.sample(len(db)//5).iterrows():
      fname = os.path.join(MEDIA_FOLDER, short_name)
      assert os.path.exists(fname)
      expected = get_metadata(fname)
      given = ({t for t in row['tags'].split()}, int(row['stars']))
      self.assertTupleEqual(given, expected, short_name)


if __name__ == '__main__':
  unittest.main()

import os
import shutil
import random
from typing import Iterable

from src.helpers import file_extension
from src.metadata import get_metadata, write_metadata

MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
METAFILE = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
BACKUP_FOLDER = os.path.join(MEDIA_FOLDER, "bak/")
EXTRA_FOLDER = os.path.join(MEDIA_FOLDER, "extra/")

SKIPLONG = ("SKIPLONG" in os.environ, "long test")


def get_initial_mediafiles() -> list[str]:
  return [f for f in os.listdir(MEDIA_FOLDER)
          if os.path.isfile(os.path.join(MEDIA_FOLDER, f))
          and file_extension(f) != 'csv']

def backup_files(fullnames:Iterable[str]) -> None:
  if not os.path.exists(BACKUP_FOLDER):
    os.mkdir(BACKUP_FOLDER)
  for f in fullnames:
    shutil.copy(f, BACKUP_FOLDER)

def inject_extra_files() -> int:
  for f in os.listdir(EXTRA_FOLDER):
    fullname = os.path.join(EXTRA_FOLDER, f)
    assert os.path.isfile(fullname)
    shutil.copy(fullname, MEDIA_FOLDER)
  return len(os.listdir(EXTRA_FOLDER))

def immitate_external_metadata_change() -> int:
  num_files = 3
  files = [os.path.join(MEDIA_FOLDER, f)
            for f in random.sample(get_initial_mediafiles(), num_files)]
  backup_files(files)
  write_metadata(files[0], tags=["canary", "canary|tagcanary"])
  write_metadata(files[1], rating=5-get_metadata(files[1])[1])
  write_metadata(files[2], tags=["finch", "finch|tagfi"], rating=5-get_metadata(files[2])[1])
  return num_files

def disk_cleanup() -> None:
  for f in os.listdir(MEDIA_FOLDER):
    if file_extension(f) == 'csv':
      os.remove(os.path.join(MEDIA_FOLDER, f))
  if os.path.exists(BACKUP_FOLDER):
    for f in os.listdir(BACKUP_FOLDER):
      shutil.move(os.path.join(BACKUP_FOLDER, f), os.path.join(MEDIA_FOLDER, f))
    os.rmdir(BACKUP_FOLDER)
  if os.path.exists(EXTRA_FOLDER):
    for f in os.listdir(EXTRA_FOLDER):
      extra_file = os.path.join(MEDIA_FOLDER, f)
      if os.path.exists(extra_file):
        os.remove(extra_file)

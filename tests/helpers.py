import os
import shutil
import random
import string
from typing import Iterable
from ae_rater_types import Outcome, ProfileInfo

from src.helpers import file_extension
from src.metadata import get_metadata, write_metadata

MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
METAFILE = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
BACKUP_INITIAL_FILE = os.path.join(MEDIA_FOLDER, 'backup_initial_metadata.csv')
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
    if not os.path.exists(os.path.join(BACKUP_FOLDER, os.path.basename(f))):
      shutil.copy(f, BACKUP_FOLDER)

def inject_extra_files() -> int:
  for f in os.listdir(EXTRA_FOLDER):
    fullname = os.path.join(EXTRA_FOLDER, f)
    assert os.path.isfile(fullname)
    shutil.copy(fullname, MEDIA_FOLDER)
  return len(os.listdir(EXTRA_FOLDER))

def remove_some_files() -> int:
  n = random.randint(1,4)
  for f in random.sample(get_initial_mediafiles(), n):
    fullname = os.path.join(MEDIA_FOLDER, f)
    backup_files([fullname])
    os.remove(fullname)
  return n

def immitate_external_metadata_change() -> tuple:
  num_files = 3
  files = [os.path.join(MEDIA_FOLDER, f)
            for f in random.sample(get_initial_mediafiles(), num_files)]
  backup_files(files)
  meta0 = get_metadata(files[0])
  meta1 = get_metadata(files[1])
  meta2 = get_metadata(files[2])
  assert not any(t in meta0.tags|meta2.tags for t in ["canary", "finch"]), str(files)
  assert 0 <= meta1.stars <= 5, files[1]
  assert 0 <= meta2.stars <= 5, files[2]
  meta0.tags = ["canary", "canary|tagcanary"]
  meta1.stars = 5 - meta1.stars
  meta2.tags = ["finch", "finch|tagfi"]
  meta2.stars = 5 - meta2.stars
  write_metadata(files[0], meta0)
  write_metadata(files[1], meta1)
  write_metadata(files[2], meta2)
  return 2, 2

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

def generate_outcome(n:int) -> Outcome:
  s = string.ascii_lowercase[:n] + ' '*random.randint(0,3*n)  # 3n to counteract bias towards draws
  s = ''.join(random.sample(s,len(s))).strip()
  return Outcome(s)

def is_sorted(l:list[ProfileInfo]) -> bool:
  for i, curr_prof in enumerate(l[:-1]):
    next_prof = l[i+1]
    if curr_prof.stars < next_prof.stars:
      assert False, f"{curr_prof}   {next_prof}"
    if all(curr_prof.ratings[s].points < next_prof.ratings[s].points
           for s in curr_prof.ratings.keys()):
      assert False, f"{curr_prof}   {next_prof}"
  return True

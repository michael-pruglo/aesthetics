#!/usr/bin/env python3

import argparse
from enum import Enum
import logging
import shutil
import os
import time
from typing import Iterable, Callable
from ae_rater_types import ManualMetadata

import helpers as hlp
from metadata import get_metadata
from udownloader import UDownloader
from down_types import UDownloaderCfg
from down_gui import DownGui


def dshell_files(cfg:UDownloaderCfg):
  """download shell (interactive prompt where user inputs internet links)"""
  udownloader = UDownloader(cfg)
  while True:
    usr_input = hlp.amnesic_input("> ")
    if usr_input.lower() == "exit":
      break
    if usr_input == "" or usr_input.isspace():
      continue

    try:
      fullname = udownloader.retreive_media(usr_input)
      yield fullname
    except:
      logging.exception("could not retreive media")
      continue

def untagged_files(dir:str):
  """catch up on already downloaded but untagged files"""
  for f in os.listdir(dir):
    fullname = os.path.join(dir, f)
    if os.path.isfile(fullname):
      has_no_meta = (get_metadata(fullname) == ManualMetadata())
      if has_no_meta:
        yield fullname

def online_usher_files(dir:str):
  """catch downloads that come outside dshell"""
  def _get_mtime():
    return os.stat(dir).st_mtime
  def _get_listdir():
    return set(os.listdir(dir))

  last_mtime = _get_mtime()
  last_listdir = _get_listdir()
  while True:
    curr_mtime = _get_mtime()
    if curr_mtime == last_mtime:
      time.sleep(1)
    elif curr_mtime > last_mtime:
      curr_listdir = _get_listdir()
      new_files = curr_listdir-last_listdir
      logging.info("observed folder got %d new files: %s",
                   len(new_files), '\n\t'.join(new_files))
      for shname in new_files:
        yield os.path.join(dir, shname)
      last_listdir = curr_listdir
      last_mtime = curr_mtime
    else:
      raise RuntimeError(f"{last_mtime} < {curr_mtime} which shouldn't happen")


class FilePrepper:
  def __init__(self, uncateg_dir):
    self.uncateg_dir = uncateg_dir

  def __call__(self, fullname:str) -> bool:
    success = self._move_if_uncategorized(fullname)
    return success

  def _move_if_uncategorized(self, fullname:str):
    ext = hlp.file_extension(fullname)
    if ext in ['png', 'gif', 'webp', 'webm']:
      logging.warning("unsupported file extension '%s', moving file to '%s'", ext, self.uncateg_dir)
      shutil.move(fullname, self.uncateg_dir)
      return False
    else:
      return True


def main(file_source:Iterable[str], file_prepper:Callable[[str],bool]=None):
  gui = DownGui()
  for fullname in file_source:
    if file_prepper and file_prepper(fullname)==False:
      continue
    gui.show_editor(fullname)


class DownMode(Enum):
  DSHELL = "dshell"
  UNTAGGED = "untagged"
  USHER = "usher"
  def __str__(self):
    return self.value


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--mode', dest='mode', type=DownMode,
                      choices=list(DownMode), default=DownMode.DSHELL,
                      help="""mode specifies the source of the media to process: 'dshell' accepts
                              links online, 'untagged' takes files already on disk, and 'usher'
                              stands by taking the newly created media files""")
  args = parser.parse_args()

  from secretcfg import UDOWNLOADER_CFG
  file_source = {
    DownMode.DSHELL: dshell_files(UDOWNLOADER_CFG),
    DownMode.UNTAGGED: untagged_files(UDOWNLOADER_CFG.dir_main),
    DownMode.USHER: online_usher_files(UDOWNLOADER_CFG.dir_main),
  }[args.mode]

  main(file_source, FilePrepper(UDOWNLOADER_CFG.dir_uncateg))

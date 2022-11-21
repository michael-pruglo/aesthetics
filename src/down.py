#!/usr/bin/env python3

import logging
import shutil

import helpers as hlp
from udownloader import UDownloader
from down_gui import DownGui


def main(cfg):
  udownloader = UDownloader(cfg)
  gui = DownGui()

  while True:
    usr_input = hlp.amnesic_input("> ")
    if usr_input.lower()=="exit":
      break
    if usr_input=="" or usr_input.isspace():
      continue

    try:
      fullname = udownloader.retreive_media(usr_input)
    except:
      logging.error("could not process input '%s'", usr_input)
      continue

    ext = hlp.file_extension(fullname)
    if ext in ['png','gif','webp','webm']:
      logging.warning("unsupported file extension '%s', moving file to '%s'", ext, cfg.uncateg_path)
      shutil.move(fullname, cfg.uncateg_path)
    else:
      gui.show_editor(fullname)


if __name__ == "__main__":
  from secretcfg import UDOWNLOADER_CFG
  main(UDOWNLOADER_CFG)

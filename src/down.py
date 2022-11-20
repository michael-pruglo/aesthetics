#!/usr/bin/env python3

import helpers as hlp
from udownloader import UDownloader
from down_gui import DownGui


def main(cfg):
  udownloader = UDownloader(cfg)
  gui = DownGui()
  while True:
    usr_input = input("> ")
    if usr_input.lower() == "exit":
      break

    try:
      fullname = udownloader.retreive_media(usr_input)
    except:
      continue

    ext = hlp.file_extension(fullname)
    if ext in ['png','webp','webm']:
      print(f"unsupported file extension '{ext}'")
    else:
      gui.show_editor(fullname)


if __name__ == "__main__":
  from secretcfg import UDOWNLOADER_CFG
  main(UDOWNLOADER_CFG)

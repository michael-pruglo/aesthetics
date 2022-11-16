#!/usr/bin/env python3

import os
import tkinter as tk
import argparse

from gui.meta_editor import MetaEditor
from ae_rater_types import ManualMetadata, ProfileInfo, UserListener
from db_managers import get_vocab
import helpers as hlp
from ai_assistant import Assistant
from metadata import write_metadata
from udownloader import UDownloader


class MockListener(UserListener):
  def consume_result(self, *args, **kwargs): pass
  def give_boost(self, *args, **kwargs): pass
  def start_next_match(self): pass
  def search_for(self, *args, **kwargs): pass
  def suggest_tags(self, fullname: str) -> list:
    return Assistant().suggest_tags(fullname)
  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    print("update_meta: ", fullname, meta)
    write_metadata(fullname, meta.tags, meta.stars, append=False)


def show_editor(fullname:str):
  root = tk.Tk()
  root.withdraw()

  meditor = MetaEditor(root, get_vocab(), MockListener())
  meditor.set_curr_profile(ProfileInfo(fullname))
  window = meditor.open(None)

  def on_destroy(e):
    if e.widget == window:
      root.quit()
  window.bind('<Destroy>', on_destroy)
  window.mainloop()

def main(args):
  fullname = UDownloader(args.dest).retreive_media(args.url)
  ext = hlp.file_extension(fullname)
  if ext in ['png','webp','webm']:
    print(f"unsupported file extension '{ext}'")
  else:
    show_editor(fullname)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('url', help="url of page with media")
  parser.add_argument('dest', help="dir media will be downloaded to")

  main(parser.parse_args())

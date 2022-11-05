#!/usr/bin/env python3

import os
import tkinter as tk

from gui.meta_editor import MetaEditor
from ae_rater_types import ManualMetadata, ProfileInfo, UserListener
from db_managers import get_vocab
import helpers as hlp


class MockListener(UserListener):
  def consume_result(self, *args, **kwargs): pass
  def give_boost(self, *args, **kwargs): pass
  def start_next_match(self): pass
  def search_for(self, *args, **kwargs): pass
  def suggest_tags(self, *args, **kwargs):
    return [('sugg',.8), ('prob',.5)]
  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    print("Update Meta: ", fullname, meta)


def download_media(url:str) -> str:
  dirr = os.path.abspath("./sample_imgs/")
  fname = "hallway.jpg"
  fullname = os.path.join(dirr,fname)
  return fullname

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

def main(url):
  fullname = download_media(url)
  ext = hlp.file_extension(fullname)
  if ext in ['png','webp','webm']:
    print(f"unsupported file extension '{ext}'")
  else:
    show_editor(fullname)


if __name__ == "__main__":
  main("")

#!/usr/bin/env python3

import sys
import os
import tkinter as tk

from gui.meta_editor import MetaEditor
from ae_rater_types import ProfileInfo, UserListener
from ai_assistant import Assistant
from metadata import ManualMetadata, get_metadata, write_metadata


class MockListener(UserListener):
  def consume_result(self, *args, **kwargs): pass
  def give_boost(self, *args, **kwargs): pass
  def start_next_match(self): pass
  def search_for(self, *args, **kwargs): pass
  def suggest_tags(self, fullname: str) -> list:
    return Assistant().suggest_tags(fullname)
  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    print("update_meta: ", fullname, meta)
    write_metadata(fullname, meta)

class DownGui:
  def __init__(self) -> None:
    self.root = tk.Tk()
    self.root.withdraw()

  def show_editor(self, fullname:str):
    meditor = MetaEditor(self.root, MockListener())
    existing_meta = get_metadata(fullname)
    prof = ProfileInfo(
      fullname=fullname,
      tags=' '.join(existing_meta.tags),
      stars=existing_meta.stars,
      awards=' '.join(existing_meta.awards),
    )
    meditor.set_curr_profile(prof)
    window = meditor.open(None)

    def on_destroy(e):
      if e.widget == window:
        self.root.quit()
    window.bind('<Destroy>', on_destroy)
    window.mainloop()


if __name__ == "__main__":
  gui = DownGui()
  for fullname in sys.argv[1:]:
    fullname = os.path.realpath(fullname)
    assert os.path.exists(fullname)
    gui.show_editor(fullname)

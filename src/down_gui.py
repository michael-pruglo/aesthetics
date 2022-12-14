import tkinter as tk

from gui.meta_editor import MetaEditor
from ae_rater_types import ManualMetadata, ProfileInfo, UserListener
from db_managers import get_vocab
from ai_assistant import Assistant
from metadata import write_metadata


class MockListener(UserListener):
  def consume_result(self, *args, **kwargs): pass
  def give_boost(self, *args, **kwargs): pass
  def start_next_match(self): pass
  def search_for(self, *args, **kwargs): pass
  def suggest_tags(self, fullname: str) -> list:
    return Assistant().suggest_tags(fullname)
  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    print("update_meta: ", fullname, meta)
    write_metadata(fullname, meta, append=False)

class DownGui:
  def __init__(self) -> None:
    self.root = tk.Tk()
    self.root.withdraw()

  def show_editor(self, fullname:str):
    meditor = MetaEditor(self.root, get_vocab(), MockListener())
    meditor.set_curr_profile(ProfileInfo(fullname))
    window = meditor.open(None)

    def on_destroy(e):
      if e.widget == window:
        self.root.quit()
    window.bind('<Destroy>', on_destroy)
    window.mainloop()

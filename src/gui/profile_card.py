import tkinter as tk
from tkinter import ttk

from ae_rater_types import ProfileInfo, Outcome
from gui.animated_element import AnimElement
from gui.meta_editor import MetaEditor
from gui.media_frame import MediaFrame
from gui.guicfg import *
import helpers as hlp


class ProfileCard(AnimElement, tk.Frame):
  def __init__(self, idx:int, checkers_color:bool, *args, **kwargs):
    tk.Frame.__init__(self, *args, **kwargs)
    self.idx = idx
    self.bg = RIGHT_COLORBG if checkers_color else LEFT_COLORBG
    self.fg = RIGHT_COLORFG if checkers_color else LEFT_COLORFG

    self.tags   = ttk.Label (self, anchor="center", foreground=self.fg, text="tags")
    self.media  = MediaFrame(self)
    self.name   = ttk.Label (self, anchor="center", foreground=self.fg, text="filename")
    self.rating = ttk.Label (self, anchor="center", foreground=self.fg, text="rating")

    TW = 0.22
    BRDR = 0.015
    PH = 0.8
    self.tags.place  (relwidth=TW,        relheight=PH,       relx=1-TW)
    self.media.place (relwidth=1-TW-BRDR, relheight=PH,       relx=BRDR)
    self.name.place  (relwidth=1,         relheight=(1-PH)/2, rely=PH)
    self.rating.place(relwidth=1,         relheight=(1-PH)/2, rely=(PH+1)/2)

  def set_meta_editor(self, *args, **kwargs):
    self.meta_editor = MetaEditor(self, *args, **kwargs)
    self.tags.bind('<Button-1>', self.meta_editor.open)
    self.master.bind(str(self.idx+1), self.meta_editor.open)

  def show_profile(self, profile:ProfileInfo) -> None:
    self.name.configure(text=hlp.short_fname(profile.fullname))
    self._show_tags(profile.tags)
    self.meta_editor.set_curr_profile(profile)
    self._show_rating(profile)
    self.media.show_media(profile.fullname)

  def get_curr_profile(self) -> ProfileInfo:
    return self.meta_editor.get_curr_profile()

  def reset_style(self) -> None:
    self.set_style(self.bg)

  def set_style(self, color:str) -> None:
    for item in self, self.tags, self.media, self.name, self.rating:
      item.configure(background=color)

  def anim_update(self):  self.media.anim_update()
  def anim_pause(self):   self.media.anim_pause()
  def anim_unpause(self): self.media.anim_unpause()

  def _show_tags(self, tags):
    tags = sorted(tags.split(' '))
    taglist = "\n".join(map(indent_hierarchical, tags))
    self.tags.configure(text=taglist or "-")

  def _show_rating(self, p:ProfileInfo):
    txt = Outcome.idx_to_let(self.idx)
    txt += "  " + '★'*int(p.stars) + u"\u2BE8"*(p.stars-int(p.stars)>.5)
    txt += f"  aw:'{p.awards}'"
    self.rating.configure(text=txt)

import tkinter as tk
from tkinter import ttk

from ae_rater_types import ProfileInfo, Outcome, RatChange
from gui.meta_editor import MetaEditor
from gui.media_frame import MediaFrame
from gui.guicfg import *
import helpers as hlp


class ProfileCard(tk.Frame):

  def __init__(self, idx:int, mode:int, *args, **kwargs):
    super().__init__(*args, **kwargs)
    is_right = idx % 2
    self.bg = RIGHT_COLORBG if is_right else LEFT_COLORBG
    self.fg = RIGHT_COLORFG if is_right else LEFT_COLORFG
    self.wincolor = RIGHT_COLORWIN if is_right else LEFT_COLORWIN
    self.drawcolor = COLORDRAW
    self.mode = mode
    self.letter = Outcome.idx_to_let(idx)

    self.tags   = ttk.Label (self, anchor="center", foreground=self.fg, text="tags")
    self.media  = MediaFrame(self)
    self.name   = ttk.Label (self, anchor="center", foreground=self.fg, text="filename")
    self.rating = ttk.Label (self, anchor="center", foreground=self.fg, text="rating")

    TW = 0.22
    BRDR = 0.015
    PH = 0.95 if self.mode==2 else 0.8
    self.tags.place  (relwidth=TW,        relheight=PH,       relx=is_right*(1-TW))
    self.media.place (relwidth=1-TW-BRDR, relheight=PH,       relx=BRDR if is_right else TW)
    self.name.place  (relwidth=1,         relheight=(1-PH)/2, rely=PH)
    self.rating.place(relwidth=1,         relheight=(1-PH)/2, rely=(PH+1)/2)

  def set_meta_editor(self, *args, **kwargs):
    self.meta_editor = MetaEditor(self, *args, **kwargs)
    self.tags.bind('<Button-1>', self.meta_editor.open)

  def show_profile(self, profile:ProfileInfo) -> None:
    self.name.configure(text=hlp.short_fname(profile.fullname))
    self._show_tags(profile.tags)
    self.meta_editor.set_curr_profile(profile)
    self._show_rating(profile.stars, profile.ratings, profile.nmatches)
    self.media.show_media(profile.fullname)

  def set_style(self, outcome:int=None, color:str=None) -> None:
    if color is None:
      if outcome is None:
        color = self.bg
      else:
        color = [self.bg, self.drawcolor, self.wincolor][outcome+1]

    for item in self, self.tags, self.media, self.name, self.rating:
      item.configure(background=color)

  def show_results(self, system_name:str, res:RatChange) -> None:
    self.rating.configure(text='; '.join([
      self.rating.cget('text'),
      f"{system_name}: {res.new_rating}({res.delta_rating:+})",
    ]))

  def pause(self):
    self.media.pause()

  def unpause(self):
    self.media.unpause()

  def _show_tags(self, tags):
    tags = sorted(tags.split(' '))
    taglist = "\n".join(map(indent_hierarchical, tags))
    self.tags.configure(text=taglist or "-")

  def _show_rating(self, stars, ratings, nmatches):
    txt = self.letter + "  " + '★'*int(stars) + u"\u2BE8"*(stars-int(stars)>.5)
    self.rating.configure(text=txt)

from functools import partial
from itertools import filterfalse
from abc import ABC, abstractmethod
import math
import tkinter as tk
from tkinter import ttk
import tkinter.font
import numpy as np
import logging

from ae_rater_types import *
from gui.animated_element import AnimElementsManager
from gui.guicfg import *
from gui.leaderboard import Leaderboard
from gui.profile_card import ProfileCard


def factorize_good_ratio(n):
  special_cases = {
    2: (2,1),
    26: (9,3),
  }
  if n in special_cases:
    return special_cases[n]

  i = n
  while i >= math.sqrt(n):
    if n%i == 0:
      cols = i
    i -= 1
  rows = n//cols
  return (cols,rows) if cols<n else factorize_good_ratio(n+1)


class RaterGui(ABC):
  def __init__(self, user_listener:UserListener):
    self.user_listener = user_listener
    self.root = tk.Tk()
    self.root.geometry(build_geometry(.87))
    self.root.title("aesthetics")
    self.root.update()

    self.style = ttk.Style(self.root)
    self.style.configure('.', background=BTFL_DARK_BG)

    self.cards:list[ProfileCard] = []
    self.animmgr = None
    self.leaderboard = Leaderboard(self.root)

    self.content_outcome = tk.StringVar()
    self.label_outcome = ttk.Label(self.root, anchor="center")
    self.input_outcome = tk.Entry(self.root, fg="#ddd", insertbackground="#ddd", insertwidth=4,
                                  font=("Arial", 14, "bold"), justify="center",
                                  textvariable=self.content_outcome, border=0,
                                  disabledbackground=BTFL_DARK_BG)
    self.input_outcome.configure(highlightthickness=0)

  def display_match(self, profiles:list[ProfileInfo], n:int=None) -> None:
    if n is None:
      n = len(profiles)
    if len(self.cards) != len(profiles):
      self._prepare_layout(n)
    self.root.update()
    self.animmgr.stop()
    for card,profile in zip(self.cards, profiles):
      card.show_profile(profile)
      card.reset_style()
    self.animmgr.run()

  def display_leaderboard(self, leaderboard:list[ProfileInfo], feat:list[ProfileInfo]=None) -> None:
    self.leaderboard.display(leaderboard, feat)

  def refresh_profile(self, prof:ProfileInfo) -> None:
    card = next(c for c in self.cards if c.get_curr_profile().fullname==prof.fullname)
    card.show_profile(prof)

  def mainloop(self):
    self.root.mainloop()

  def _prepare_layout(self, n:int):
    assert 1 < n <= 26, f"cannot show gui for {n} cards"
    for c in self.cards:
      c.destroy()
    self.cards = []
    self.style.configure('TLabel', font=("Arial", 9), foreground="#ccc")
    COLS, ROWS = factorize_good_ratio(n)
    LDBRD_W = 0.24 if False else 0.125  # TODO: make profiles for 1080p and 4k
    SINGLE_W = (1-LDBRD_W)/COLS
    INP_H = 0.055
    INP_LBL_H = INP_H*0.35
    for i in range(n):
      col, row = i%COLS, i//COLS
      checkers_color = (col+row)%2
      card = ProfileCard(i, checkers_color, self.root)
      card.set_meta_editor(self.user_listener)
      card.place(relx=col*SINGLE_W, rely=row*(1/ROWS), relwidth=SINGLE_W, relheight=1/ROWS)
      self.cards.append(card)
    self.animmgr = AnimElementsManager(self.root, self.cards)
    self.leaderboard.place(relx=1-LDBRD_W, relheight=1-INP_H, relwidth=LDBRD_W)
    self.label_outcome.place(relx=1-LDBRD_W, rely=1-INP_H, relheight=INP_LBL_H, relwidth=LDBRD_W)
    self.input_outcome.place(relx=1-LDBRD_W, rely=1-INP_H+INP_LBL_H, relheight=INP_H-INP_LBL_H, relwidth=LDBRD_W)
    self.input_outcome.focus()

  def _enable_input(self, enable:bool, n:int=0):
    if enable:
      self.input_outcome.config(state=tk.NORMAL, background="#444")
      self.input_outcome.delete(0, tk.END)
      self.input_outcome.bind('<Return>', partial(self._on_input_received, n=n))
    else:
      self.input_outcome.config(state=tk.DISABLED)
      self.input_outcome.unbind('<Return>')

  @abstractmethod
  def _on_input_received(self, event, n):
    pass


class MatchGui(RaterGui):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.scheduled_jobs:list[str] = []

  def display_match(self, profiles, n=None):
    super().display_match(profiles, n)
    self.label_outcome.configure(text="enter outcome string:")
    self._enable_input(True, n)

  def _prepare_layout(self, n):
    super()._prepare_layout(n)
    self.content_outcome.trace_add("write", lambda a,b,c: self._highlight_curr_outcome(n))

  def _highlight_curr_outcome(self, n:int):
    for card in self.cards:
      card.reset_style()

    input_so_far = self.content_outcome.get()
    input_so_far = ''.join(filterfalse(str.isdigit, input_so_far))
    self.content_outcome.set(input_so_far)

    bgcolor = "#444"
    if not Outcome.is_valid(input_so_far, n, intermediate=True):
      bgcolor = RED_ERR
    else:
      if Outcome.is_valid(input_so_far, n):
        bgcolor = "#141"
      tiers, max_tier = Outcome.predict_tiers_intermediate(input_so_far, n)
      MAXCOLOR = 0x99
      color_intensities = np.linspace(0, MAXCOLOR, max_tier)
      for idx, tier in tiers.items():
        x = color_intensities[tier]
        tier_color = f"#{int(x):02x}{MAXCOLOR-int(x):02x}00"
        self.cards[idx].set_style(tier_color)

    self.input_outcome.configure(background=bgcolor)

  def _on_input_received(self, event, n):
    s = self.input_outcome.get()
    logging.info("usr input '%s'", s)
    if Outcome.is_valid(s, n):
      self._enable_input(False)
      self.user_listener.consume_result(Outcome(s))
    else:
      self.input_outcome.config(background=RED_ERR)

  def conclude_match(self) -> None:
    job_id = self.root.after(CHANGE_MATCH_DELAY, self.user_listener.start_next_match)
    self.scheduled_jobs.append(job_id)

  def mainloop(self):
    super().mainloop()
    for id in self.scheduled_jobs:
      self.root.after_cancel(id)
    self.scheduled_jobs = []



class SearchGui(RaterGui):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.search_page = 1
    for arrow in ["<Up>", "<Down>"]:
      self.root.bind(arrow, self._on_arrow)
    self._enable_input(True)

  def _on_arrow(self, event):
    if event.keysym == "Up":
      if self.search_page == 1:
        return
      self.search_page -= 1
    else:
      self.search_page += 1
    self._on_input_received(None, None)

  def _on_input_received(self, event, n):
    if event is not None:
      self.search_page = 1
    self.user_listener.search_for(self.input_outcome.get(), self.search_page)

  def display_match(self, profiles, n=None):
    super().display_match(profiles, n)
    self.label_outcome.configure(text=f"[page #{self.search_page}] search query:")

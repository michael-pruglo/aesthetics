import tkinter as tk
from dataclasses import dataclass
import numpy as np

from gui.guicfg import *
from ae_rater_types import Outcome, ProfileInfo
import helpers as hlp

class Leaderboard(tk.Text):
  @dataclass
  class LineVisualCfg:
    bgs: list[str]
    is_featured: bool
    fgfeatured: str
    spacing: int
    textfixs: list[str]

  def __init__(self, master) -> None:
    super().__init__(master, padx=0, pady=10, bd=0, cursor="arrow",
            font=tk.font.Font(family='courier 10 pitch', size=9), background=BTFL_DARK_BG)
    super().configure(highlightthickness=0)
    self.HEAD_LEN = 5

  def display(self, leaderboard, feature, outcome, context:int=2):
    """ display top and everyone from `feature` and `context` lines around them """
    self.configure(state=tk.NORMAL)
    self.delete("1.0", tk.END)

    displayed_rows:dict[int,str] = {}
    for i in range(min(self.HEAD_LEN, len(leaderboard))):
      displayed_rows.setdefault(i, "")

    for i, featured in enumerate(feature):
      letter = Outcome.idx_to_let(i)
      rank = next(j for j,p in enumerate(leaderboard) if p.fullname==featured.fullname)
      for j in range(max(0,rank-context), min(len(leaderboard),rank+context+1)):
        displayed_rows.setdefault(j, "")
      displayed_rows[rank] = letter

    self.tag_configure('total_matches', foreground=BTFL_LIGHT_GRAY, justify="center", spacing3=10)
    self.insert(tk.END, f"total matches: {sum([p.nmatches for p in leaderboard])//2}\n", 'total_matches')
    prev = -1
    for i in sorted(displayed_rows.keys()):
      if i-prev != 1:
        self.tag_configure('chunk_break', foreground=BTFL_LIGHT_GRAY, justify="center", spacing1=10, spacing3=10)
        self.insert(tk.END, "...\n", 'chunk_break')
      self._write_profile(i, leaderboard[i], displayed_rows[i], len(feature)==2, outcome)
      prev = i

    self.configure(state=tk.DISABLED)

  def _write_profile(self, idx:int, prof:ProfileInfo, letter:str, both_sides:bool, outcome):
    cfg = self._get_line_visual_cfg(letter, both_sides, outcome)

    tagfix = 'tag_prefix'+str(idx)
    self.tag_configure(tagfix, background=cfg.bgs[0], foreground=cfg.fgfeatured, spacing1=cfg.spacing, spacing3=cfg.spacing)
    self.insert(tk.END, cfg.textfixs[0], tagfix)

    for tag,fg,txt in self._get_display_blueprint(idx, prof):
      if cfg.is_featured:
        fg = {
          'tag_idx': cfg.fgfeatured,
          'tag_name': cfg.fgfeatured,
        }.get(tag, fg)
      tag += str(idx)
      self.tag_configure(tag, background=cfg.bgs[1], foreground=fg, spacing1=cfg.spacing, spacing3=cfg.spacing)
      self.insert(tk.END, txt, tag)

    tagfix = 'tag_suffix'+str(idx)
    self.tag_configure(tagfix, background=cfg.bgs[2], foreground=cfg.fgfeatured, spacing1=cfg.spacing, spacing3=cfg.spacing)
    self.insert(tk.END, cfg.textfixs[1], tagfix)

    self.insert(tk.END, '\n')

  def _get_line_visual_cfg(self, letter, both_sides, outcome) -> LineVisualCfg:
    default_bg = BTFL_DARK_BG
    lenfix = 3
    featured_spacing = 10

    if letter == "":
      return self.LineVisualCfg(
        bgs = [default_bg, "#282828", default_bg],
        is_featured = False,
        fgfeatured = BTFL_LIGHT_GRAY,
        spacing = 0,
        textfixs = [' '*lenfix,' '*lenfix],
      )

    if both_sides:
      if letter == "a":
        outcome_bg = {
          Outcome("a b"): LEFT_COLORWIN,
          Outcome("ab"): COLORDRAW,
          Outcome("b a"): LEFT_COLORBG,
        }.get(outcome, LEFT_COLORBG)
        return self.LineVisualCfg(
          bgs = [outcome_bg]*2 + [default_bg],
          is_featured = True,
          fgfeatured = LEFT_COLORFG,
          spacing = featured_spacing,
          textfixs = ['<'*lenfix,' '*lenfix],
        )
      else:
        assert letter == "b"
        outcome_bg = {
          Outcome("a b"): RIGHT_COLORBG,
          Outcome("ab"): COLORDRAW,
          Outcome("b a"): RIGHT_COLORWIN,
        }.get(outcome, RIGHT_COLORBG)
        return self.LineVisualCfg(
          bgs = [default_bg] + [outcome_bg]*2,
          is_featured = True,
          fgfeatured = RIGHT_COLORFG,
          spacing = featured_spacing,
          textfixs = [' '*lenfix,'>'*lenfix],
        )
    else:
      return self.LineVisualCfg(
        bgs = [LEFT_COLORWIN if outcome else LEFT_COLORBG]*2 + [default_bg],
        is_featured = True,
        fgfeatured = LEFT_COLORFG,
        spacing = featured_spacing,
        textfixs = [' '+letter+' ',' '*lenfix],
      )

  def _get_display_blueprint(self, idx, prof) -> list[tuple[str,str,str]]:
    rat_color = ["#777", "#9AB4C8", "#62B793", "#C9C062", "#FF8701", "#E0191f"][min(5, int(prof.stars))]
    nmatches_color = int(np.interp(prof.nmatches, [0,100], [0x70,255]))
    return [
      ('tag_idx', "#aaa", f"{idx+1:>4} "),
      ('tag_name', "#ddd", f"{hlp.truncate(hlp.short_fname(prof.fullname), 15, '..'):<15} "),
      ('tag_stars', BTFL_DARK_GRANOLA, str('*'*int(prof.stars)+'\''*(prof.stars%1>=.5)).ljust(6)),
    ] + [
      (f'tag_rating{sysname}', rat_color, f"{str(rat):>9} ")
      for sysname,rat in prof.ratings.items()
    ] + [
      ('tag_nmatches', "#"+f"{nmatches_color:02x}"*3, f"{f'({prof.nmatches})':<5}"),
    ]

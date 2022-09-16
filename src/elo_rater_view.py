from numpy import interp
from enum import Enum, auto
import tkinter as tk
from tkinter import ttk
import tkinter.font
from typing import Callable
from PIL import ImageTk, Image, ImageOps
from tkVideoPlayer import TkinterVideo

from helpers import short_fname, truncate
from elo_rater_types import EloChange, Outcome, ProfileInfo


LEFT_BG = "#353935"
RIGHT_BG = "#353539"
BTFL_DARK_BG = "#222"
BTFL_DARK_PINE = "#234F1E"
BTFL_DARK_GRANOLA = "#D6B85A"
BTFL_LIGHT_MINT = "#99EDC3"
BTFL_LIGHT_GRAY = "#ccc"

class MediaFrame(tk.Frame): # tk and not ttk, because the former supports .configure(background=)
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.img = None
    self.img_frame = None
    self.vid_frame = None
    self.err_label = None

  def show_media(self, fname):
    ext = fname.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png', 'gif']:
      self.show_img(fname)
    elif ext in ['mp4', 'mov']:
      self.show_vid(fname)
    else:
      self.show_err(f"cannot open {fname}: unsupported extension .{ext}")

  def show_img(self, fname):
    self.unpack()
    if self.img_frame is None:
      self.img_frame = ttk.Label(self)
    self.img = Image.open(fname)
    self.img = ImageOps.contain(self.img, (self.winfo_width(), self.winfo_height()))
    self.img = ImageTk.PhotoImage(self.img)
    self.img_frame.config(image=self.img)
    self.img_frame.pack(expand=True)

  def show_vid(self, fname):
    self.unpack()
    if self.vid_frame is None:
      self.vid_frame = TkinterVideo(self, keep_aspect=True)
      self.vid_frame.configure(background=BTFL_DARK_BG)
    self.vid_frame.load(fname)
    self.vid_frame.pack(expand=True, fill="both")
    self.vid_frame.bind("<<Ended>>", lambda _: self.vid_frame.play())
    self.vid_frame.play()

  def show_err(self, error_str):
    self.unpack()
    if self.err_label is None:
      self.err_label = ttk.Label(self, wraplength=self.winfo_width()-60)
    self.err_label.config(text=error_str, font=("Arial", 20, "bold"), foreground="red")
    self.err_label.pack(expand=True)

  def unpack(self):
    for elem in [self.img_frame, self.vid_frame, self.err_label]:
      if elem:
        elem.pack_forget()
    if self.vid_frame:
      self.vid_frame.unbind("<<Ended>>")
      self.vid_frame = None #slower, but stop+reuse the existing causes bugs
    self.update()

class ProfileCard(tk.Frame):
  def __init__(self, idx:int, *args, **kwargs):
    super().__init__(*args, **kwargs)
    is_right  = idx%2
    self.bg = RIGHT_BG if is_right else LEFT_BG

    self.tags   = ttk.Label (self, anchor="center", text="tags")
    self.media  = MediaFrame(self)
    self.name   = ttk.Label (self, anchor="center", text="filename")
    self.rating = ttk.Label (self, anchor="center", text="rating", foreground="yellow")

    TW = 0.22
    BRDR = 0.015
    PH = 0.95
    self.tags.place  (relx=is_right*(1-TW),   relwidth=TW,   relheight=PH)
    self.media.place (relx=BRDR if is_right else TW, relwidth=1-TW-BRDR, relheight=PH)
    self.name.place  (rely=PH,                relwidth=1,    relheight=(1-PH)/2)
    self.rating.place(rely=(PH+1)/2,          relwidth=1,    relheight=(1-PH)/2)

  def show_profile(self, profile:ProfileInfo) -> None:
    self.name.configure(text=short_fname(profile.fullname))
    self._show_tags(profile.tags)
    self._show_rating(profile.rating, profile.elo, profile.elo_matches)
    self.media.show_media(profile.fullname)

  def set_style(self, outcome:int=None) -> None:
    if outcome is None:
      color = self.bg
    else:
      color = [self.bg, BTFL_DARK_GRANOLA, BTFL_DARK_PINE][outcome+1]
    for item in self, self.tags, self.media, self.name, self.rating:
      item.configure(background=color)

  def show_results(self, res:EloChange) -> None:
    self.rating.configure(text=f"NEW: {res.new_elo}  ({res.delta_elo:+})")

  def _show_tags(self, tags):
    tags = sorted(tags.split(' '))
    def indent_hierarchical(t):
      return "  "*t.count('|') + t.split('|')[-1]
    taglist = "\n".join(map(indent_hierarchical, tags))
    self.tags.configure(text=taglist or "-")

  def _show_rating(self, rating, elo, elo_matches):
    self.rating.configure(text=f"{'★'*rating}  {elo} (matches: {elo_matches})")

class Leaderboard(tk.Text):
  class FeatureType(Enum):
    NONE = auto()
    LEFT = auto()
    RIGHT = auto()

  def __init__(self, master) -> None:
    super().__init__(master, padx=0, pady=10, bd=0, cursor="arrow",
            font=tk.font.Font(family='courier 10 pitch', size=9), background=BTFL_DARK_BG)
    super().configure(highlightthickness=0)
    self.HEAD_LEN = 5

  def display(self, leaderboard, feature, context:int=2):
    """ display top and everyone from `feature` and `context` lines around them """
    self.configure(state=tk.NORMAL)
    self.delete("1.0", tk.END)

    displayed_rows = {}
    for i in range(min(self.HEAD_LEN, len(leaderboard))):
      displayed_rows.setdefault(i, self.FeatureType.NONE)
    for featured,feature_type in zip(feature, [self.FeatureType.LEFT, self.FeatureType.RIGHT]):
      rank = next(i for i,p in enumerate(leaderboard) if p.fullname==featured.fullname)
      for i in range(max(0,rank-context), min(len(leaderboard),rank+context+1)):
        displayed_rows.setdefault(i, self.FeatureType.NONE)
      displayed_rows[rank] = feature_type

    prev = -1
    for i in sorted(displayed_rows.keys()):
      if i-prev != 1:
        self.tag_configure('chunk_break', foreground=BTFL_LIGHT_GRAY, justify="center", spacing1=10, spacing3=10)
        self.insert(tk.END, "...\n", 'chunk_break')
      self._write_profile(i, leaderboard[i], displayed_rows[i])
      prev = i

    self.configure(state=tk.DISABLED)

  def _write_profile(self, idx:int, prof:ProfileInfo, feat:FeatureType=FeatureType.NONE):
    blueprint = self._get_display_blueprint(idx, prof)

    default_bg = BTFL_DARK_BG
    lenfix = 3
    bgs = [default_bg, "#282828", default_bg]
    textfixs = [' '*lenfix,' '*lenfix]
    spacing = 0
    if feat == self.FeatureType.LEFT:
      bgs = [LEFT_BG]*2 + [default_bg]
      textfixs = ['<'*lenfix,' '*lenfix]
      spacing = 9
    if feat == self.FeatureType.RIGHT:
      bgs = [default_bg] + [RIGHT_BG]*2
      textfixs = [' '*lenfix,'>'*lenfix]
      spacing = 9

    tagfix = 'tag_prefix'+str(idx)
    self.tag_configure(tagfix, background=bgs[0], foreground=BTFL_LIGHT_GRAY, spacing1=spacing, spacing3=spacing)
    self.insert(tk.END, textfixs[0], tagfix)

    for tag,(fg,txt) in blueprint.items():
      tag += str(idx)
      self.tag_configure(tag, background=bgs[1], foreground=fg, spacing1=spacing, spacing3=spacing)
      self.insert(tk.END, txt, tag)

    tagfix = 'tag_suffix'+str(idx)
    self.tag_configure(tagfix, background=bgs[2], foreground=BTFL_LIGHT_GRAY, spacing1=spacing, spacing3=spacing)
    self.insert(tk.END, textfixs[1], tagfix)

    self.insert(tk.END, '\n')
  """
      special_bg = None
      if feat == self.FeatureType.LEFT:
        special_bg = "#505050"
        blueprint['tag_prefix'] = (BTFL_LIGHT_GRAY, special_bg, "<<")
      if feat == self.FeatureType.RIGHT:
        special_bg = "#707070"
        blueprint['tag_suffix'] = (BTFL_LIGHT_GRAY, special_bg, ">>")
      for tag,(fg,bg,txt) in blueprint.items():
        tag += str(idx)
        self.tag_configure(tag, background=special_bg or bg, foreground=fg)
        self.insert(tk.END, txt, tag)
      self.insert(tk.END, '\n')
  """

  def _get_display_blueprint(self, idx, prof) -> list[tuple]:
    elo_m_shade = int(interp(prof.elo_matches, [0,100], [0x70,255]))
    default_bg = "#303030"
    return {
      'tag_idx': ("#aaa", f"{idx+1:>3} "),
      'tag_name': ("#ddd", f"{truncate(short_fname(prof.fullname), 15, '..'):<15} "),
      'tag_rating': (BTFL_DARK_GRANOLA, f"{'*' * prof.rating:>5} "),
      'tag_elo': (
        ["#777", "#9AB4C8", "#62B793", "#C9C062", "#FF8701", "#E0191f"][prof.rating],
        f"{prof.elo:>4} ",
      ),
      'tag_elo_matches': ("#"+f"{elo_m_shade:02x}"*3, f"{f'({prof.elo_matches})':<5}"),
    }


class EloGui:
  def __init__(self):
    self.root = tk.Tk()
    self.root.geometry("1766x878+77+77")
    self.root.title("aesthetics")
    self.root.update()

    style = ttk.Style(self.root)
    style.configure('.', background=BTFL_DARK_BG)
    style.configure('TLabel', font=("Arial", 11), foreground="#ccc")

    self.curr_profiles:list[ProfileInfo] = [None, None]
    self.cards        :list[ProfileCard] = [None, None]
    MID_W = 0.166
    for i in range(2):
      self.cards[i] = ProfileCard(i, self.root)
      self.cards[i].place(relx=i*(0.5+MID_W/2), relwidth=0.5-MID_W/2, relheight=1)
    self.leaderboard = Leaderboard(self.root)
    self.leaderboard.place(relx=0.5-MID_W/2, relwidth=MID_W, relheight=1)
    self.report_outcome_cb = None

  def display_match(self, profiles:list[ProfileInfo], callback:Callable[[Outcome],None]) -> None:
    assert len(profiles) == 2
    for card,profile in zip(self.cards, profiles):
      card.show_profile(profile)
      card.set_style(None)
    self.curr_profiles = profiles
    self.report_outcome_cb = callback
    self._enable_arrows(True)

  def conclude_match(self, results:list[EloChange], callback:Callable) -> None:
    for card,res in zip(self.cards, results):
      card.show_results(res)
    for profile,res in zip(self.curr_profiles, results):
      profile.elo = res.new_elo
      profile.elo_matches += 1
    self.root.after(3000, callback)

  def display_leaderboard(self, leaderboard:list[ProfileInfo], feature:list[ProfileInfo]=None) -> None:
    self.leaderboard.display(leaderboard, feature)

  def mainloop(self):
    self.root.mainloop()

  def _enable_arrows(self, enable:bool):
    for key in '<Left>', '<Right>', '<Up>':
      if enable:
        self.root.bind(key, self._on_arrow_press)
      else:
        self.root.unbind(key)

  def _on_arrow_press(self, event):
    self._enable_arrows(False)
 
    outcome = {
      "Left": Outcome.WIN_LEFT,
      "Up": Outcome.DRAW,
      "Right": Outcome.WIN_RIGHT,
    }[event.keysym]
    self.cards[0].set_style(-outcome.value)
    self.cards[1].set_style( outcome.value)
    self.report_outcome_cb(outcome)

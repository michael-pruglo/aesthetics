import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image, ImageOps
from tkVideoPlayer import TkinterVideo

from elo_rater_types import EloChange, Outcome, ProfileInfo


BTFL_DARK_BG = "#222"
BTFL_DARK_PINE = "#234F1E"
BTFL_DARK_GRANOLA = "#D6B85A"
BTFL_LIGHT_MINT = "#99EDC3"

class MediaFrame(ttk.Frame):
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
    def loop_if_not_changed(_):
      # if not self.vid_frame.is_paused():
      self.vid_frame.play()
    self.vid_frame.bind("<<Ended>>", loop_if_not_changed)
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
      self.vid_frame.stop()
    self.update()


class ProfileCard(ttk.Frame):
  def __init__(self, idx:int, *args, **kwargs):
    super().__init__(*args, **kwargs)
    is_bottom = idx>1
    is_right  = idx%2

    PREV_H = 0.15
    self.place(
      relx = 0.5*is_right,
      rely = PREV_H*is_bottom,
      relwidth = 0.5,
      relheight = 1-PREV_H if is_bottom else PREV_H
    )

    self.tags   = ttk.Label (self, anchor="center", text="tags")
    self.media  = MediaFrame(self, borderwidth=1, relief="ridge")
    self.name   = ttk.Label (self, anchor="center", text="filename")
    self.rating = ttk.Label (self, anchor="center", text="rating", foreground="yellow")

    TW = 0.25 if is_bottom else 0
    PH = 0.95 if is_bottom else 0.7
    self.tags.place  (relx=is_right*(1-TW),   relwidth=TW,   relheight=PH)
    self.media.place (relx=TW*(not is_right), relwidth=1-TW, relheight=PH)
    self.name.place  (rely=PH,                relwidth=1,    relheight=(1-PH)/2)
    self.rating.place(rely=(PH+1)/2,          relwidth=1,    relheight=(1-PH)/2)

  def show_profile(self, profile:ProfileInfo) -> None:
    self.name.configure(text=profile.short_name())
    self._show_tags(profile.tags)
    self._show_rating(profile.rating, profile.elo, profile.elo_matches)
    self.media.show_media(profile.fullname)

  def set_style(self, outcome:int=None) -> None:
    if outcome is None:
      color = BTFL_DARK_BG
    else:
      color = [BTFL_DARK_BG, BTFL_DARK_GRANOLA, BTFL_DARK_PINE][outcome+1]
    for item in self.name, self.rating, self.tags:
      item.configure(background=color)

  def show_results(self, new_elo:int, delta_elo:int) -> None:
    self.rating.configure(text=f"NEW: {new_elo}  ({delta_elo:+})")

  def _show_tags(self, tags):
    tags = sorted(tags.split(' '))
    def indent_hierarchical(t):
      return "  "*t.count('|') + t.split('|')[-1]
    taglist = "\n".join(map(indent_hierarchical, tags))
    self.tags.configure(text=taglist or "-")

  def _show_rating(self, rating, elo, elo_matches):
    self.rating.configure(text=f"{'★'*rating}  {elo} (matches: {elo_matches})")


class EloGui:
  def __init__(self):
    self.root = tk.Tk()
    self.root.geometry("1766x878+77+77")
    self.root.title("aesthetics")
    self.root.update()

    self.root.configure(background=BTFL_DARK_BG)
    style = ttk.Style(self.root)
    style.configure('.', background=BTFL_DARK_BG)
    style.configure('TLabel', font=("Arial", 11), foreground="#ccc")

    self.cards = [ProfileCard(i, self.root, borderwidth=1, relief="ridge") for i in range(4)]
    self.curr_profile1 = None
    self.curr_profile2 = None

    self.report_outcome = None

  def display_match(self, profile1:ProfileInfo, profile2:ProfileInfo, callback) -> None:
    if self.curr_profile1 and self.curr_profile2:
      self.cards[0].show_profile(self.curr_profile1)
      self.cards[1].show_profile(self.curr_profile2)
    self.cards[2].show_profile(profile1)
    self.cards[3].show_profile(profile2)
    self.cards[2].set_style(None)
    self.cards[3].set_style(None)
    self._enable_arrows(True)
    self.curr_profile1 = profile1
    self.curr_profile2 = profile2
    self.report_outcome = callback

  def conclude_match(self, res:EloChange, callback) -> None:
    self.cards[2].show_results(res.new_elo_1, res.delta_elo_1)
    self.cards[3].show_results(res.new_elo_2, res.delta_elo_2)
    self.curr_profile1.elo_matches += 1
    self.curr_profile1.elo = res.new_elo_1
    self.curr_profile2.elo_matches += 1
    self.curr_profile2.elo = res.new_elo_2
    self.root.after(1000, callback)

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
    self.cards[2].set_style(-outcome.value)
    self.cards[3].set_style( outcome.value)
    self.report_outcome(outcome)

from functools import partial
import tkinter as tk
from tkinter import ttk
import tkinter.font
from typing import Callable
import numpy as np
from PIL import ImageTk, Image, ImageOps
from tkVideoPlayer import TkinterVideo

import helpers as hlp
from ae_rater_types import *


CHANGE_MATCH_DELAY = 1500
ACC_TAG_THRESH = 0.47

BTFL_DARK_BG = "#222"
BTFL_DARK_GRANOLA = "#D6B85A"
BTFL_LIGHT_GRAY = "#ccc"

LEFT_COLORBG = "#353935"
RIGHT_COLORBG = "#353539"
spice_fg_rgb  = lambda r,g,b: tuple([int(max(x*1.2,255) if x==max(r,g,b) else x) for x in (r,g,b)])
spice_fg_hsl  = lambda h,s,l: (h, .1, .6)
spice_win_hsl = lambda h,s,l: (h, .3, .3)
LEFT_COLORFG   = hlp.spice_up_color(LEFT_COLORBG,   spice_fg_rgb,  spice_fg_hsl)
RIGHT_COLORFG  = hlp.spice_up_color(RIGHT_COLORBG,  spice_fg_rgb,  spice_fg_hsl)
LEFT_COLORWIN  = hlp.spice_up_color(LEFT_COLORBG,   None, spice_win_hsl)
RIGHT_COLORWIN = hlp.spice_up_color(RIGHT_COLORBG,  None, spice_win_hsl)
COLORDRAW      = hlp.spice_up_color(RIGHT_COLORWIN, None, lambda h,s,l: (60, s, l))


def indent_hierarchical(tag:str, indent:int=2) -> str:
  return " "*tag.count('|')*indent + tag.rsplit('|', maxsplit=1)[-1]


class MediaFrame(tk.Frame): # tk and not ttk, because the former supports .configure(background=)
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.img = None
    self.img_frame = None
    self.vid_frame = None
    self.err_label = None
    self.media_fname = ""

  def show_media(self, fname):
    self.media_fname = fname
    ext = hlp.file_extension(fname)
    if ext in ['jpg', 'jpeg', 'png', 'jfif', 'webp', 'heic']:
      self.show_img(fname)
    elif ext in ['mp4', 'mov', 'gif']:
      self.show_vid(fname)
    else:
      self.show_err(f"cannot open {fname}: unsupported extension .{ext}")

  def show_img(self, fname):
    self.unpack()
    if self.img_frame is None:
      self.img_frame = ttk.Label(self, cursor="hand2")
      self.img_frame.bind('<Button-1>', self._open_media_in_new_window)
    self.img = Image.open(fname)
    selfsize = (self.winfo_width(), self.winfo_height())
    assert selfsize > (10,10)
    self.img = ImageOps.contain(self.img, selfsize)
    self.img = ImageTk.PhotoImage(self.img)
    self.img_frame.config(image=self.img)
    self.img_frame.pack(expand=True)

  def show_vid(self, fname):
    self.unpack()
    if self.vid_frame is None:
      self.vid_frame = TkinterVideo(self, keep_aspect=True)
      self.vid_frame.configure(background=BTFL_DARK_BG, cursor="hand2")
      self.vid_frame.bind('<Button-1>', self._open_media_in_new_window)
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
      self.vid_frame = None  # slower, but stop+reuse the existing causes bugs
    self.update()

  def _open_media_in_new_window(self, event):
    if not self.media_fname:
      print(f"Gui error on click media: cannot open {event}")
    else:
      hlp.start_file(self.media_fname)


class ProfileCard(tk.Frame):
  class MetaEditor:
    def __init__(self, master, vocab:list[str], update_meta_cb:Callable[[str,list],None],
                 suggest_tags_cb:Callable[[str],list]):
      self.master = master
      self.vocab = vocab if vocab[0] else vocab[1:]
      self.update_meta_cb = update_meta_cb
      self.suggest_tags_cb = suggest_tags_cb
      self.curr_prof = None
      self.stars:int = None
      self.win = None

    def set_curr_profile(self, prof:ProfileInfo):
      self.curr_prof = prof
      self.stars = int(prof.stars)

    def open(self, event):
      assert self.curr_prof
      assert self.stars is not None
      print(f"open tag editor for {hlp.short_fname(self.curr_prof.fullname)}")
      print(f"{self.curr_prof.tags.split()}")
      print( "suggested tags:")
      try:
        suggested_tags = self.suggest_tags_cb(self.curr_prof.fullname)
      except:
        suggested_tags = []

      self._create_window(suggested_tags)

    def _create_window(self, suggested_tags):
      self.win = tk.Toplevel(self.master)
      self.win.title(f"edit meta {hlp.short_fname(self.curr_prof.fullname)}")
      self.win.geometry("1500x800+210+140")

      self._configure_style()

      self.stars_lbl = ttk.Label(self.win, justify=tk.CENTER, style="IHateTkinter.TLabel")  # just WHY will it not justify?
      self._update_stars()
      for i in range(6):
        self.win.bind(str(i), self._update_stars)

      commit_button = ttk.Button(self.win, text="COMMIT", command=self._on_commit_pressed, style="IHateTkinter.TButton")
      vscroll = ttk.Scrollbar(self.win, style="IHateTkinter.Vertical.TScrollbar")
      tag_container_canvas = tk.Canvas(self.win, yscrollcommand=vscroll.set)
      vscroll.config(command=tag_container_canvas.yview)
      tag_frame = ttk.Frame(tag_container_canvas, style="IHateTkinter.TFrame")
      media_panel = MediaFrame(self.win)
      sugg_panel = tk.Text(self.win, padx=0, pady=10, bd=0, cursor="arrow", spacing1=8,
                            foreground=BTFL_LIGHT_GRAY, background=BTFL_DARK_BG,
                            font=tk.font.Font(family='courier 10 pitch', size=9))
      self._display_suggestions(suggested_tags, sugg_panel)

      LW, MW = .5, .22
      RW = 1 - (LW + MW)
      TH = .95
      CHBXW = .95
      media_panel.place(relwidth=LW, relheight=1)
      tag_container_canvas.place(relwidth=MW*CHBXW, relheight=TH, relx=LW)
      vscroll.place(relwidth=MW*(1-CHBXW), relheight=TH, relx=LW+MW*CHBXW)
      self.stars_lbl.place(relwidth=MW*.5, relheight=1-TH, relx=LW, rely=TH)
      commit_button.place(relwidth=MW*.5, relheight=1-TH, relx=LW+MW*.5, rely=TH)
      sugg_panel.place(relwidth=RW, relheight=1, relx=LW+MW)
      self.win.update()
      tag_container_canvas.create_window(LW, 0, window=tag_frame, anchor="nw", width=MW*CHBXW*self.win.winfo_width())

      media_panel.show_media(self.curr_prof.fullname)
      self._populate_checkboxes(tag_frame, suggested_tags)
      self.win.update()
      self._enable_mousewheel_scroll_you_stupid_tkinter(tag_container_canvas)
      tag_container_canvas.config(scrollregion=tag_container_canvas.bbox(tk.ALL))

    def _display_suggestions(self, suggested_tags, sugg_panel:tk.Text):
      sugg_panel.configure(state=tk.NORMAL)
      sugg_panel.delete("1.0", tk.END)
      sugg_panel.tag_configure('heading', justify="center")
      sugg_panel.insert(tk.END, "SUGGESTED TAGS:\n", 'heading')
      for tag, prob in suggested_tags:
        sugg_panel.tag_configure('acc_line', foreground="#383")
        sugg_panel.insert(tk.END, f"\n{tag:>20} {prob*100:>5.2f} {'#'*int(prob*30)}", 'acc_line' if prob>ACC_TAG_THRESH else '')
      sugg_panel.configure(state=tk.DISABLED)

    def _configure_style(self):
      self.style = ttk.Style(self.win)
      for elem in ["TButton", "TCheckbutton", "TFrame", "Vertical.TScrollbar"]:
        self.style.map("IHateTkinter."+elem,
        foreground = [('active', "#fff"), ('!active', BTFL_LIGHT_GRAY)],
        background = [('active', "#555")],
        indicatorcolor = [('selected', "#0f0")],
      )
      self.style.configure("IHateTkinter.TCheckbutton", indicatorcolor="#444", padding=2)
      self.style.configure("IHateTkinter.TLabel", foreground=BTFL_DARK_GRANOLA, font=(None, 20))

    def _populate_checkboxes(self, master, suggested_tags):
      def should_be_set(tag):
        prob = next((p for t,p in suggested_tags if t==tag), 0)
        return (tag in self.curr_prof.tags) or (self.curr_prof.tags=="" and prob > ACC_TAG_THRESH)

      self.states = {tag:tk.IntVar(self.win, int(should_be_set(tag))) for tag in self.vocab}

      def check_parent_as_well():
        for tag,var in self.states.items():
          if var.get():
            par = tag.split('|')
            for i in range(1, len(par)):
              parent = '|'.join(par[:i])
              self.states[parent].set(1)

      for tag in self.states:
        stylename = "IHateTkinter.TCheckbutton"
        prob = next((p for t,p in suggested_tags if t==tag), None)
        if prob:
          stylename = f"sugg{int(prob*30)}." + stylename
          self.style.configure(stylename, background=f"#3{3+int(prob*10):x}3")
        chk_btn = ttk.Checkbutton(master, text=indent_hierarchical(tag, 6),
                                  command=check_parent_as_well, variable=self.states[tag],
                                  style=stylename)
        chk_btn.pack(expand=True, fill=tk.X, padx=20)

    def _enable_mousewheel_scroll_you_stupid_tkinter(self, scrollable):
      def _on_mousewheel(event):
        dir = 0
        if event.num == 5 or event.delta == -120:
          dir = 1
        if event.num == 4 or event.delta == 120:
          dir = -1
        scrollable.yview_scroll(dir*2, "units")
      self.win.bind_all("<MouseWheel>", _on_mousewheel)
      self.win.bind_all("<Button-4>", _on_mousewheel)
      self.win.bind_all("<Button-5>", _on_mousewheel)

    def _update_stars(self, event=None):
      if event is not None:
        self.stars = int(event.keysym)
      self.stars_lbl.configure(text='★'*self.stars+'☆'*(5-self.stars))

    def _on_commit_pressed(self):
      selected = [tag for tag, var in self.states.items() if var.get()]
      self.update_meta_cb(self.curr_prof.fullname, tags=selected, stars=self.stars)
      self.win.destroy()

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
    self.tag_editor = self.MetaEditor(self, *args, **kwargs)
    self.tags.bind('<Button-1>', self.tag_editor.open)

  def show_profile(self, profile:ProfileInfo) -> None:
    self.name.configure(text=hlp.short_fname(profile.fullname))
    self._show_tags(profile.tags)
    self.tag_editor.set_curr_profile(profile)
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

  def _show_tags(self, tags):
    tags = sorted(tags.split(' '))
    taglist = "\n".join(map(indent_hierarchical, tags))
    self.tags.configure(text=taglist or "-")

  def _show_rating(self, stars, ratings, nmatches):
    txt = self.letter + "  " + '★'*int(stars) + u"\u2BE8"*(stars-int(stars)>.5)
    self.rating.configure(text=txt)


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


class RaterGui:
  def __init__(self, user_listener:UserListener, tags_vocab:list[str]):
    self.user_listener = user_listener
    self.tags_vocab = tags_vocab
    self.root = tk.Tk()
    self.root.geometry("1766x878+77+77")
    self.root.title("aesthetics")
    self.root.update()

    self.style = ttk.Style(self.root)
    self.style.configure('.', background=BTFL_DARK_BG)

    self.curr_prof_shnames:list[str] = []
    self.cards:list[ProfileCard] = []
    self.leaderboard = Leaderboard(self.root)
    self.help = ttk.Label(self.root, background="#333", anchor='s',
                          justify="center", padding=(10,10),
                          text="<-/-> to choose winner\n^ to draw\nCtrl+ <-/-> to give boost")

    self.content_outcome = tk.StringVar()
    self.label_outcome = ttk.Label(self.root, anchor="center", text="enter outcome string:")
    self.input_outcome = tk.Entry(self.root, fg="#ddd", insertbackground="#ddd", insertwidth=4,
                                  font=("Arial", 14, "bold"), justify="center",
                                  textvariable=self.content_outcome, border=0,
                                  disabledbackground=BTFL_DARK_BG)
    self.input_outcome.configure(highlightthickness=0)
    self.scheduled_jobs = []

  def display_match(self, profiles:list[ProfileInfo]) -> None:
    n = len(profiles)
    if len(self.cards) != n:
      self._prepare_layout(n)
    self.root.update()
    for card,profile in zip(self.cards, profiles):
      card.show_profile(profile)
      card.set_style(None)
    self.curr_prof_shnames = [hlp.short_fname(p.fullname) for p in profiles]
    if n == 2:
      self._enable_arrows(True)
    else:
      self._enable_input(True, n)

  def conclude_match(self, opinions:RatingOpinions) -> None:
    for system_name,changes in opinions.items():
      for card,change in zip(self.cards, changes):
        card.show_results(system_name, change)

    job_id = self.root.after(CHANGE_MATCH_DELAY, self.user_listener.start_next_match)
    self.scheduled_jobs.append(job_id)

  def display_leaderboard(self, leaderboard:list[ProfileInfo],
                          feature:list[ProfileInfo]=None, outcome:Outcome=None) -> None:
    self.leaderboard.display(leaderboard, feature, outcome)

  def mainloop(self):
    self.root.mainloop()
    for id in self.scheduled_jobs:
      self.root.after_cancel(id)

  def _prepare_layout(self, n:int):
    if n==2:
      self.style.configure('TLabel', font=("Arial", 11), foreground="#ccc")
      LDBRD_W = 0.24  # TODO: fix width
      HELP_H = 0.07
      for i in range(n):
        card = ProfileCard(i, n, self.root)
        card.set_meta_editor(self.tags_vocab, self.user_listener.update_meta, self.user_listener.suggest_tags)
        card.place(relx=i*(0.5+LDBRD_W/2), relwidth=0.5-LDBRD_W/2, relheight=1)
        self.cards.append(card)
      self.leaderboard.place(relx=0.5-LDBRD_W/2, relwidth=LDBRD_W, relheight=1-HELP_H)
      self.help.place(relx=0.5-LDBRD_W/2, rely=1-HELP_H, relwidth=LDBRD_W, relheight=HELP_H)
      self.label_outcome.place_forget()
      self.input_outcome.place_forget()
    elif 2 < n <= 12:
      self.style.configure('TLabel', font=("Arial", 9), foreground="#ccc")
      ROWS = 1 if n<6 else 2
      COLS = (n+ROWS-1)//ROWS
      LDBRD_W = 0.24
      SINGLE_W = (1-LDBRD_W)/COLS
      INP_H = 0.055
      INP_LBL_H = INP_H*0.35
      for i in range(n):
        card = ProfileCard(i, n, self.root)
        card.set_meta_editor(self.tags_vocab, self.user_listener.update_meta, self.user_listener.suggest_tags)
        card.place(relx=i%COLS*SINGLE_W, rely=i//COLS*0.5, relwidth=SINGLE_W, relheight=1/ROWS)
        self.cards.append(card)
      self.leaderboard.place(relx=1-LDBRD_W, relheight=1-INP_H, relwidth=LDBRD_W)
      self.label_outcome.place(relx=1-LDBRD_W, rely=1-INP_H, relheight=INP_LBL_H, relwidth=LDBRD_W)
      self.input_outcome.place(relx=1-LDBRD_W, rely=1-INP_H+INP_LBL_H, relheight=INP_H-INP_LBL_H, relwidth=LDBRD_W)
      self.input_outcome.focus()
      self.content_outcome.trace_add("write", lambda a,b,c: self._highlight_curr_outcome(n))
    else:
      raise NotImplementedError(f"cannot show gui for {n} cards")

  def _highlight_curr_outcome(self, n:int):
    for card in self.cards:
      card.set_style(None)

    input_so_far = self.content_outcome.get()
    bgcolor = "#444"
    if not Outcome.is_valid(input_so_far, n, intermediate=True):
      bgcolor = "#911"
    else:
      if Outcome.is_valid(input_so_far, n):
        bgcolor = "#141"
      tiers, max_tier = Outcome.predict_tiers_intermediate(input_so_far, n)
      MAXCOLOR = 0x99
      color_intensities = np.linspace(0, MAXCOLOR, max_tier)
      for idx, tier in tiers.items():
        x = color_intensities[tier]
        tier_color = f"#{int(x):02x}{MAXCOLOR-int(x):02x}00"
        self.cards[idx].set_style(color=tier_color)

    self.input_outcome.configure(background=bgcolor)

  def _enable_arrows(self, enable:bool):
    for key in '<Left>', '<Right>', '<Up>':
      boost_seq = f'<Control-{key[1:-1]}>'
      if enable:
        self.root.bind(key, self._on_arrow_press)
        self.root.bind(boost_seq, self._on_give_boost)
      else:
        self.root.unbind(key)
        self.root.unbind(boost_seq)

  def _on_arrow_press(self, event):
    self._enable_arrows(False)

    outcome = {
      "Left": (Outcome("a b"), -1),
      "Up":   (Outcome("ab"),   0),
      "Right":(Outcome("b a"),  1),
    }[event.keysym]
    self.cards[0].set_style(outcome=-outcome[1])
    self.cards[1].set_style(outcome= outcome[1])
    self.root.update()
    self.user_listener.consume_result(outcome[0])

  def _enable_input(self, enable:bool, n:int=0):
    if enable:
      self.input_outcome.config(state=tk.NORMAL, background="#444")
      self.input_outcome.delete(0, tk.END)
      self.input_outcome.bind('<Return>', partial(self._on_input_received, n=n))
    else:
      self.input_outcome.config(state=tk.DISABLED)
      self.input_outcome.unbind('<Return>')

  def _on_input_received(self, event, n):
    s = self.input_outcome.get()
    if Outcome.is_valid(s, n):
      outcome = Outcome(s)
      for idx, mult in outcome.get_boosts().items():
        self.user_listener.give_boost(self.curr_prof_shnames[idx], mult)
      self._enable_input(False)
      self.user_listener.consume_result(outcome)
    else:
      self.input_outcome.config(background="#911")

  def _on_give_boost(self, event):
    assert len(self.curr_prof_shnames) == 2
    is_right = (event.keysym=="Right")
    self.user_listener.give_boost(self.curr_prof_shnames[is_right], 1)

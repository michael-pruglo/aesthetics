import tkinter as tk
from tkinter import ttk
import tkinter.font
from typing import Callable

from ae_rater_types import  ProfileInfo, UserListener
from metadata import ManualMetadata
from tags_vocab import VOCAB
from gui.media_frame import MediaFrame
from gui.guicfg import *
import helpers as hlp


class TagEditor(ttk.Frame):
  class Autocomplete:
    def __init__(self, parent) -> None:
      self.parent:TagEditor = parent
      self.hits = []
      self.prev_style = ""

    def on_tag_entered(self, e):
      CTRL = 4
      if e.state & CTRL:
        return

      if self.hits:
        curr_val = self.parent.states[self.hits[0]].get()
        self.parent.states[self.hits[0]].set(1-curr_val)
        self.parent._check_parent_as_well()
        self.parent.tag_entry.delete(0, tk.END)
        self.parent.tag_entry.configure(background=BTFL_DARK_BG)
      else:
        self.parent.tag_entry.configure(background=RED_ERR)

    def dehighlight_prev(self):
      assert self.prev_style
      self.parent.chk_btns[self.hits[0]].configure(style=self.prev_style)

    def highlight(self, tag):
        self.prev_style = self.parent.chk_btns[tag].cget('style')
        self.parent.chk_btns[tag].configure(style="Entered.IHateTkinter.TCheckbutton")
        self.parent.tag_entry.configure(background=BTFL_DARK_BG)
        i = sorted(VOCAB).index(tag)
        percent = i/len(self.parent.states)
        self.parent.tag_container_canvas.yview_moveto(percent-.1)

    def refresh(self, a,b,c):
      if self.hits:
        self.dehighlight_prev()

      entered = self.parent.content_tag_entry.get().lower()
      if entered and not (entered[-1].isalpha() or entered[-1] in "_|2"):
        entered = entered[:-1]
        self.parent.content_tag_entry.set(entered)

      self.hits = []
      if entered:
        for tag in VOCAB:
          if entered in tag.rsplit('|', maxsplit=1)[-1]:
            if not self.hits:
              self.highlight(tag)
            self.hits.append(tag)

      if entered and not self.hits:
        self.parent.tag_entry.configure(background=RED_ERR)

    def next_hit(self, e):
      if len(self.hits)<2:
        return
      self.dehighlight_prev()
      self.hits = self.hits[1:] + self.hits[:1]
      self.highlight(self.hits[0])
      return "break"


  def __init__(self, curr_prof:ProfileInfo, suggested_tags:list[str],
               on_commit_cb:Callable[[ManualMetadata],None], style, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.style = style
    self.states = {}
    self.chk_btns = {}
    self.curr_prof = curr_prof
    self.stars = int(curr_prof.stars)
    self.suggested_tags = suggested_tags
    self.on_commit_cb = on_commit_cb
    self.autocomplete = TagEditor.Autocomplete(self)
    self.content_tag_entry = tk.StringVar()
    self.content_award_entry = tk.StringVar()

    self.style.configure("IHateTkinter.TCheckbutton", indicatorcolor="#444", padding=2)
    self.style.configure("Entered.IHateTkinter.TCheckbutton", background="#991")

  def create_children(self):
    self.style.configure("G.IHateTkinter.TLabel", foreground=BTFL_DARK_GRANOLA,
                         background=BTFL_DARK_BG, font=(None, 18))  # just WHY will it not inherit style?
    self.stars_lbl = ttk.Label(self, justify=tk.CENTER, style="G.IHateTkinter.TLabel")  # just WHY will it not justify?
    self._update_stars()
    for i in range(7):
      self.bind_all(str(i), self._update_stars)

    commit_button = ttk.Button(self, text="COMMIT", command=self._on_commit_pressed, style="IHateTkinter.TButton")
    self.bind_all("<Control-Return>", lambda e: self._on_commit_pressed())
    vscroll = ttk.Scrollbar(self, style="IHateTkinter.Vertical.TScrollbar")
    self.tag_container_canvas = tk.Canvas(self, yscrollcommand=vscroll.set)
    vscroll.config(command=self.tag_container_canvas.yview)
    tag_frame = ttk.Frame(self.tag_container_canvas, style="IHateTkinter.TFrame")

    self.tag_entry = tk.Entry(self, fg="#ddd", bg=BTFL_DARK_BG,
                              insertbackground="#ddd", insertwidth=4,
                              font=("Arial", 14, "bold"), justify="center",
                              textvariable=self.content_tag_entry,
                              disabledbackground=BTFL_DARK_BG)
    self.tag_entry.focus()
    self.content_tag_entry.trace_add("write", self.autocomplete.refresh)
    self.tag_entry.bind("<Tab>", self.autocomplete.next_hit)
    self.tag_entry.bind("<Return>", self.autocomplete.on_tag_entered)

    self.award_entry = tk.Entry(self, fg="#ddd", bg=BTFL_DARK_BG,
                              insertbackground="#ddd", insertwidth=4,
                              font=("Arial", 14, "bold"), justify="left",
                              textvariable=self.content_award_entry,
                              disabledbackground=BTFL_DARK_BG)
    self.content_award_entry.set(self.curr_prof.awards)

    TH = .9
    ENTH = .05
    CHBXW = .95

    self.tag_container_canvas.place(relwidth=CHBXW, relheight=TH)
    vscroll.place(relwidth=1-CHBXW, relheight=TH, relx=CHBXW)
    self.stars_lbl.place(relwidth=.5, relheight=1-TH-ENTH, rely=TH+ENTH)
    commit_button.place(relwidth=.5, relheight=1-TH-ENTH, relx=.5, rely=TH+ENTH)
    self.tag_entry.place(relwidth=1, relheight=ENTH/2, rely=TH)
    self.award_entry.place(relwidth=1, relheigh=ENTH/2, rely=TH+ENTH/2)

    self.tag_container_canvas.create_window(0, 0, window=tag_frame, anchor="nw", width=CHBXW*self.winfo_width())
    self._populate_checkboxes(tag_frame)
    self.update()
    self._enable_mousewheel_scroll_you_stupid_tkinter()
    self.tag_container_canvas.config(scrollregion=self.tag_container_canvas.bbox(tk.ALL))

  def _populate_checkboxes(self, master):
    self.states = {tag:tk.IntVar(self, int(self._should_be_set(tag))) for tag in sorted(VOCAB)}

    for tag in self.states:
      stylename = "IHateTkinter.TCheckbutton"
      prob = next((p for t,p in self.suggested_tags if t==tag), None)
      if prob:
        stylename = f"sugg{int(prob*30)}." + stylename
        self.style.configure(stylename, background=f"#3{3+int(prob*10):x}3")
      self.chk_btns[tag] = ttk.Checkbutton(master, text=indent_hierarchical(tag, 6),
                                           command=self._check_parent_as_well, variable=self.states[tag],
                                           style=stylename)
      self.chk_btns[tag].pack(expand=True, fill=tk.X, padx=20)

  def _should_be_set(self, tag):
    prob = next((p for t,p in self.suggested_tags if t==tag), 0)
    return (tag in self.curr_prof.tags) or (self.curr_prof.tags=="" and prob > ACC_TAG_THRESH)

  def _check_parent_as_well(self):
    for tag,var in self.states.items():
      if var.get():
        par = tag.split('|')
        for i in range(1, len(par)):
          parent = '|'.join(par[:i])
          self.states[parent].set(1)
    self.tag_entry.focus()

  def _enable_mousewheel_scroll_you_stupid_tkinter(self):
    def _on_mousewheel(event):
      dir = 0
      if event.num == 5 or event.delta == -120:
        dir = 1
      if event.num == 4 or event.delta == 120:
        dir = -1
      self.tag_container_canvas.yview_scroll(dir*2, "units")
    self.bind_all("<MouseWheel>", _on_mousewheel)
    self.bind_all("<Button-4>", _on_mousewheel)
    self.bind_all("<Button-5>", _on_mousewheel)

  def _update_stars(self, event=None):
    if event is not None:
      self.stars = int(event.keysym)
    self.stars_lbl.configure(text='★'*self.stars+'☆'*(5-self.stars))

  def _on_commit_pressed(self):
    input_meta = ManualMetadata(
      tags={tag for tag, var in self.states.items() if var.get()},
      stars=self.stars,
      awards=set(self.content_award_entry.get().split()),
    )
    self.on_commit_cb(input_meta)

  def cleanup(self):
    for i in range(7):
      self.unbind_all(str(i))


class MetaEditor:
  def __init__(self, master, user_listener:UserListener):
    self.master = master
    self.user_listener = user_listener
    self.curr_prof = None
    self.win = None
    self.tag_editor:TagEditor = None
    self.job_id = ""

  def set_curr_profile(self, prof:ProfileInfo):
    self.curr_prof = prof

  def get_curr_profile(self) -> ProfileInfo:
    return self.curr_prof

  def open(self, event) -> tk.Toplevel:
    assert self.curr_prof
    try:
      suggested_tags = self.user_listener.suggest_tags(self.curr_prof.fullname)
    except:
      suggested_tags = []
    self._create_window(suggested_tags)
    assert self.win
    return self.win

  def _create_window(self, suggested_tags):
    self.win = tk.Toplevel(self.master)
    self.win.protocol("WM_DELETE_WINDOW", self._cleanup)
    self.win.title(f"edit meta {hlp.short_fname(self.curr_prof.fullname)}")
    self.win.geometry(build_geometry((0.6, 0.8)))

    self._configure_style()

    self.media_panel = MediaFrame(self.win)
    self.tag_editor = TagEditor(self.curr_prof, suggested_tags,
                                self._on_commit_pressed, self.style, self.win)
    sugg_panel = tk.Text(self.win, padx=0, pady=10, bd=0, cursor="arrow", spacing1=8,
                          foreground=BTFL_LIGHT_GRAY, background=BTFL_DARK_BG,
                          font=tk.font.Font(family='courier 10 pitch', size=9))
    self._display_suggestions(suggested_tags, sugg_panel)

    LW, MW = .5, .22
    RW = 1 - (LW + MW)

    self.media_panel.place(relwidth=LW, relheight=1)
    self.tag_editor.place(relwidth=MW, relheight=1, relx=LW)
    sugg_panel.place(relwidth=RW, relheight=1, relx=LW+MW)
    self.win.update()
    self.tag_editor.create_children()
    self.media_panel.show_media(self.curr_prof.fullname)
    self.anim_update()

  def anim_update(self):
    self.media_panel.anim_update()
    self.job_id = self.win.after(10, self.anim_update)

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
    self.style.configure('.', background=BTFL_DARK_BG)
    for elem in ["TButton", "TCheckbutton", "TFrame", "Vertical.TScrollbar"]:
      self.style.map("IHateTkinter."+elem,
        foreground = [('active', "#fff"), ('!active', BTFL_LIGHT_GRAY)],
        background = [('active', "#555")],
        indicatorcolor = [('selected', "#0f0")],
      )

  def _on_commit_pressed(self, meta:ManualMetadata):
    self.user_listener.update_meta(self.curr_prof.fullname, meta)
    self._cleanup()

  def _cleanup(self):
    if self.media_panel:
      self.media_panel.anim_pause()
    if self.job_id:
      self.win.after_cancel(self.job_id)
      self.job_id = ""
    self.tag_editor.cleanup()
    self.win.destroy()

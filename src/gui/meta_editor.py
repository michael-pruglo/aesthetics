import tkinter as tk
from tkinter import ttk
import tkinter.font
from typing import Callable

from ae_rater_types import ProfileInfo
from gui.media_frame import MediaFrame
from gui.guicfg import *
import helpers as hlp


class TagEditor(ttk.Frame):
  def __init__(self, vocab:list[str], curr_prof:ProfileInfo, suggested_tags:list[str],
               on_commit_cb:Callable[[list,int],None], style, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.style = style
    self.vocab = vocab
    self.curr_prof = curr_prof
    self.stars = int(curr_prof.stars)
    self.suggested_tags = suggested_tags
    self.on_commit_cb = on_commit_cb
    self.content_tag_entry = tk.StringVar()

  def create_children(self):
    self.stars_lbl = ttk.Label(self, justify=tk.CENTER, style="IHateTkinter.TLabel")  # just WHY will it not justify?
    self._update_stars()
    for i in range(6):
      self.bind(str(i), self._update_stars)

    commit_button = ttk.Button(self, text="COMMIT", command=self._on_commit_pressed, style="IHateTkinter.TButton")
    self.bind("<Control-Return>", lambda e: self._on_commit_pressed())
    vscroll = ttk.Scrollbar(self, style="IHateTkinter.Vertical.TScrollbar")
    tag_container_canvas = tk.Canvas(self, yscrollcommand=vscroll.set)
    vscroll.config(command=tag_container_canvas.yview)
    tag_frame = ttk.Frame(tag_container_canvas, style="IHateTkinter.TFrame")

    self.tag_entry = tk.Entry(self, fg="#ddd", bg=BTFL_DARK_BG,
                              insertbackground="#ddd", insertwidth=4,
                              font=("Arial", 14, "bold"), justify="center",
                              textvariable=self.content_tag_entry,
                              disabledbackground=BTFL_DARK_BG)
    self.tag_entry.focus()

    TH = .9
    ENTH = .05
    CHBXW = .95

    tag_container_canvas.place(relwidth=CHBXW, relheight=TH)
    vscroll.place(relwidth=1-CHBXW, relheight=TH, relx=CHBXW)
    self.stars_lbl.place(relwidth=.5, relheight=1-TH-ENTH, rely=TH+ENTH)
    commit_button.place(relwidth=.5, relheight=1-TH-ENTH, relx=.5, rely=TH+ENTH)
    self.tag_entry.place(relwidth=1, relheight=ENTH, rely=TH)

    tag_container_canvas.create_window(0, 0, window=tag_frame, anchor="nw", width=CHBXW*self.winfo_width())
    self._populate_checkboxes(tag_frame, self.suggested_tags)
    self.update()
    self._enable_mousewheel_scroll_you_stupid_tkinter(tag_container_canvas)
    tag_container_canvas.config(scrollregion=tag_container_canvas.bbox(tk.ALL))

  def _populate_checkboxes(self, master, suggested_tags):
    def should_be_set(tag):
      prob = next((p for t,p in suggested_tags if t==tag), 0)
      return (tag in self.curr_prof.tags) or (self.curr_prof.tags=="" and prob > ACC_TAG_THRESH)

    self.states = {tag:tk.IntVar(self, int(should_be_set(tag))) for tag in self.vocab}

    def check_parent_as_well():
      for tag,var in self.states.items():
        if var.get():
          par = tag.split('|')
          for i in range(1, len(par)):
            parent = '|'.join(par[:i])
            self.states[parent].set(1)

    def on_tag_entered(e):
      tag = self.content_tag_entry.get()
      print("tag entered:", tag)
      if tag in self.states:
        curr_val = self.states[tag].get()
        self.states[tag].set(1-curr_val)
        check_parent_as_well()
        self.tag_entry.delete(0, tk.END)
        self.tag_entry.configure(background=BTFL_DARK_BG)
      else:
        self.tag_entry.configure(background=RED_ERR)
    self.tag_entry.bind("<Return>", on_tag_entered)

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
    self.bind_all("<MouseWheel>", _on_mousewheel)
    self.bind_all("<Button-4>", _on_mousewheel)
    self.bind_all("<Button-5>", _on_mousewheel)

  def _update_stars(self, event=None):
    if event is not None:
      self.stars = int(event.keysym)
    self.stars_lbl.configure(text='★'*self.stars+'☆'*(5-self.stars))

  def _on_commit_pressed(self):
    selected = [tag for tag, var in self.states.items() if var.get()]
    self.on_commit_cb(selected, self.stars)


class MetaEditor:
  def __init__(self, master, vocab:list[str], update_meta_cb:Callable[[str,list],None],
                suggest_tags_cb:Callable[[str],list]):
    self.master = master
    self.vocab = vocab if vocab[0] else vocab[1:]  # TODO: fix
    self.update_meta_cb = update_meta_cb
    self.suggest_tags_cb = suggest_tags_cb
    self.curr_prof = None
    self.win = None
    self.tag_editor:TagEditor = None

  def set_curr_profile(self, prof:ProfileInfo):
    self.curr_prof = prof

  def open(self, event):
    assert self.curr_prof
    try:
      suggested_tags = self.suggest_tags_cb(self.curr_prof.fullname)
    except:
      suggested_tags = []
    self._create_window(suggested_tags)

  def _create_window(self, suggested_tags):
    self.win = tk.Toplevel(self.master)
    self.win.title(f"edit meta {hlp.short_fname(self.curr_prof.fullname)}")
    self.win.geometry(build_geometry((0.6, 0.8)))

    self._configure_style()

    media_panel = MediaFrame(self.win)
    self.tag_editor = TagEditor(self.vocab, self.curr_prof, suggested_tags,
                                self._on_commit_pressed, self.style, self.win)
    sugg_panel = tk.Text(self.win, padx=0, pady=10, bd=0, cursor="arrow", spacing1=8,
                          foreground=BTFL_LIGHT_GRAY, background=BTFL_DARK_BG,
                          font=tk.font.Font(family='courier 10 pitch', size=9))
    self._display_suggestions(suggested_tags, sugg_panel)

    LW, MW = .5, .22
    RW = 1 - (LW + MW)

    media_panel.place(relwidth=LW, relheight=1)
    self.tag_editor.place(relwidth=MW, relheight=1, relx=LW)
    sugg_panel.place(relwidth=RW, relheight=1, relx=LW+MW)
    self.win.update()
    self.tag_editor.create_children()
    media_panel.show_media(self.curr_prof.fullname)

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

  def _on_commit_pressed(self, selected, stars):
    self.update_meta_cb(self.curr_prof.fullname, tags=selected, stars=stars)
    self.win.destroy()

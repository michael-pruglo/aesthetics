import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image, ImageOps
from tkVideoPlayer import TkinterVideo

from gui.guicfg import BTFL_DARK_BG
import helpers as hlp


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
    if ext in ['jpg', 'jpeg', 'png', 'jfif', 'webp']:
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
      self.vid_frame.stop()
      self.vid_frame = None  # slower, but reusng the existing causes bugs
    self.update()

  def pause(self):
    if self.vid_frame:
      self.vid_frame.pause()

  def unpause(self):
    if self.vid_frame:
      self.vid_frame.play()

  def _open_media_in_new_window(self, event):
    if not self.media_fname:
      print(f"Gui error on click media: cannot open {event}")
    else:
      hlp.start_file(self.media_fname)

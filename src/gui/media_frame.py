import time
import logging
import os
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk, Image, ImageOps
import imageio

from gui.animated_element import AnimElement
from gui.guicfg import BTFL_DARK_BG
import helpers as hlp


class MediaFrame(AnimElement, tk.Frame): # tk and not ttk, because the former supports .configure(background=)
  def __init__(self, *args, **kwargs):
    tk.Frame.__init__(self, *args, **kwargs)
    self.configure(background=BTFL_DARK_BG)

    self.media_fname = ""
    self.img = None
    self.vid_reader = None
    self.vid_stream_time = 0
    self.fps = 0
    self.paused = False

    self.lbl = ttk.Label(self, border=0, cursor="hand2")
    self.lbl.bind('<Button-1>', self._open_media_in_new_window)
    self.lbl.pack(expand=True)

  def show_media(self, fname):
    self.update()
    if self.vid_reader:
      self.vid_reader.close()
      self.vid_reader = None

    self.media_fname = fname
    ext = hlp.file_extension(fname)
    if ext in ['jpg', 'jpeg', 'png', 'jfif', 'webp']:
      self._display_image(Image.open(fname))
    elif ext in ['mp4', 'mov', 'gif']:
      self.vid_reader = imageio.get_reader(fname)
      self.fps = self.vid_reader.get_meta_data().get('fps', 30)
      self.last_update_time = None
      self._stream_vid_from_beginning()
    else:
      self.lbl.config(image="", text=f"cannot open {fname}: unsupported extension .{ext}",
                      font=("Arial", 20, "bold"), foreground="red", wraplength=self.winfo_width()-50)

  def _display_image(self, img:Image):
    winsize = (self.winfo_width(), self.winfo_height())
    assert all(px>10 for px in winsize), winsize
    self.img = ImageOps.contain(img, winsize)
    self.img = ImageTk.PhotoImage(self.img)
    self.lbl.config(image=self.img)

  def _stream_vid_from_beginning(self):
    self.vid_stream_time = time.time_ns()
    tmp, self.paused = self.paused, False  # to always show the 1st frame
    self.anim_update()
    self.paused = tmp

  def anim_update(self):
    if self.vid_reader is None or self.paused:
      return
    now = time.time_ns()
    ms_elapsed = (now - self.vid_stream_time) / 1e6
    idx = round(self.fps * ms_elapsed / 1000)
    if self.last_update_time:
      delta_t = (now - self.last_update_time) / 1e6
      TOO_MUCH_LAG = 520
      if delta_t > TOO_MUCH_LAG:
        logging.error("too much lag on video %s: %.2fms [idx=%d]", os.path.basename(self.media_fname), delta_t, idx)
        self.anim_pause()
        return
    self.last_update_time = now
    try:
      img_array = self.vid_reader.get_data(idx)
      self._display_image(Image.fromarray(img_array))
    except IndexError:
      self._stream_vid_from_beginning()

  def anim_pause(self):
    self.paused = True

  def anim_unpause(self):
    self.paused = False
    self._stream_vid_from_beginning()

  def _open_media_in_new_window(self, event):
    assert self.media_fname
    hlp.start_file(self.media_fname)

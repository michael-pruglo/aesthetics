import os
import shutil
import logging
import time
from dataclasses import dataclass
from send2trash import send2trash

import helpers as hlp
from down_gui import DownGui
from metadata import get_metadata, has_metadata


class Converter:
  def __init__(self) -> None:
    self.acceptable_ext = ["jpg", "jpeg", "mp4", "jfif", "mov"]
    self.conversion_map = {
      "png": self.convert_png,
      "heic": self.convert_heic,
    }

  def needs_conversion(self, fname:str) -> bool:
    return hlp.file_extension(fname) not in self.acceptable_ext

  def can_convert(self, fname:str) -> bool:
    return hlp.file_extension(fname) in self.conversion_map

  def convert(self, fullname:str, keep_original:bool=True) -> str:
    assert os.path.exists(fullname)
    ext = hlp.file_extension(fullname)
    converted_name = self.conversion_map[ext](fullname)
    assert os.path.exists(converted_name)
    if not keep_original:
      send2trash(fullname)
    return converted_name

  def convert_png(self, fullname) -> str:
    self._exec(f"mogrify -format jpg '{fullname}'", fullname)
    return self._get_converted_fname(fullname, "jpg")

  def convert_heic(self, fullname) -> str:
    conv_fname = self._get_converted_fname(fullname, "jpg")
    self._exec(f"heif-convert -q 100 '{fullname}' '{conv_fname}'", fullname)
    return conv_fname

  def convert_gif(self, fullname) -> str:
    pass
  def convert_webp_vid(self, fullname) -> str:
    pass
  def convert_webp_img(self, fullname) -> str:
    pass

  def _exec(self, cmd:str, fullname:str) -> None:
    assert os.path.exists(fullname)
    tmp_wd = os.path.dirname(fullname)
    global_wd = os.getcwd()
    if global_wd != tmp_wd:
      os.chdir(tmp_wd)
    logging.info("executing command:\n\t%s\n\tworking_dir=%s", cmd, os.getcwd())
    os.system(cmd)
    if global_wd != tmp_wd:
      os.chdir(global_wd)

  def _get_converted_fname(self, fullname:str, out_ext:str) -> str:
    return f"{os.path.splitext(fullname)[0]}.{out_ext}"


@dataclass
class UsherCfg:
  buffer_dir: str
  uncateg_dir: str
  dest_dir: str

  def __post_init__(self) -> None:
    assert os.path.exists(self.buffer_dir)
    assert os.path.exists(self.uncateg_dir)
    assert os.path.exists(self.dest_dir)


class Usher:
  def __init__(self, cfg:UsherCfg) -> None:
    self.cfg = cfg
    self.gui = DownGui()
    self.converter = Converter()

  def idle(self) -> None:
    last_mtime = None
    while True:
      if last_mtime == os.stat(self.cfg.buffer_dir).st_mtime:
        time.sleep(2)
      else:
        catch_up = 1
        self.process_recent_files(1+catch_up)
        last_mtime = os.stat(self.cfg.buffer_dir).st_mtime

  def process_recent_files(self, n_interactive:int) -> None:
    buffer_files = [os.path.join(self.cfg.buffer_dir, f) for f in os.listdir(self.cfg.buffer_dir)]
    buffer_files = filter(os.path.isfile, buffer_files)
    for fullname in sorted(buffer_files, key=os.path.getmtime, reverse=True):
      if n_interactive == 0:
        break
      n_interactive -= self.process_file(fullname)

  def process_file(self, fullname) -> bool:
    logging.info("process_file '%s'", fullname)
    was_interactive = False

    if self.converter.needs_conversion(fullname):
      if self.converter.can_convert(fullname):
        logging.info("Converting...")
        fullname = self.converter.convert(fullname, keep_original=False)
      else:
        logging.warning("unsupported file extension '%s'", fullname)
        logging.warning("moving file to '%s'", self.cfg.uncateg_dir)
        shutil.move(fullname, self.cfg.uncateg_dir)
        return False

    conflict_fname = os.path.join(self.cfg.dest_dir, os.path.basename(fullname))
    if os.path.exists(conflict_fname):
      print("File already exists:")
      print(f"\t{conflict_fname}")
      print(f"\t{get_metadata(conflict_fname)}")
      while True:
        usr_input = hlp.amnesic_input("do you want to skip and remove the contender? [y/n]: ").lower()
        if usr_input in ["y", "yes"]:
          send2trash(fullname)
          return False
        elif usr_input in ["n", "no"]:
          new_fullname = '_contend'.join(os.path.splitext(fullname))
          os.rename(fullname, new_fullname)
          return self.process_file(new_fullname)

    if not has_metadata(fullname):
      self.gui.show_editor(fullname)
      was_interactive = True
    else:
      logging.info("file already has metadata:\n\t%s", get_metadata(fullname))

    logging.info("Processing done. Moving file...\n\n\n")
    shutil.move(fullname, self.cfg.dest_dir)

    return was_interactive

import os
import shutil
import logging
import time
from dataclasses import dataclass
from send2trash import send2trash

import helpers as hlp
from down_gui import DownGui
from metadata import can_write_metadata, get_metadata, has_metadata


class Converter:
  def __init__(self) -> None:
    self.acceptable_ext = ["jpg", "jpeg", "mp4", "jfif", "mov"]
    self.conversion_map = {
      "png":  ("jpg", lambda fin,fout: f"mogrify -format jpg '{fin}'"),
      "heic": ("jpg", lambda fin,fout: f"heif-convert -q 100 '{fin}' '{fout}'"),
      "webp": ("jpg", lambda fin,fout: f"ffmpeg -loglevel error -i '{fin}' '{fout}'"),
      "webm": ("mp4", lambda fin,fout: f"ffmpeg -loglevel warning -i '{fin}' '{fout}'"),
      "gif":  ("mp4", lambda fin,fout: f"ffmpeg -loglevel warning -i '{fin}' -movflags faststart -pix_fmt yuv420p -vf \"scale=trunc(iw/2)*2:trunc(ih/2)*2\" '{fout}'"),
      # webp_vid might be: f'convert '{fin}' frames.png && ffmpeg -i frames-%0d.png -c:v libx264 -movflags faststart -pix_fmt yuv420p -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" {fout}; rm frames*png'
    }

  def needs_conversion(self, fname:str) -> bool:
    return hlp.file_extension(fname) not in self.acceptable_ext

  def can_convert(self, fname:str) -> bool:
    return hlp.file_extension(fname) in self.conversion_map

  def convert(self, fullname:str, keep_original:bool=True) -> str:
    assert os.path.exists(fullname)
    assert self.can_convert(fullname)
    out_ext, get_conv_cmd = self.conversion_map[hlp.file_extension(fullname)]
    converted_name = f"{os.path.splitext(fullname)[0]}.{out_ext}"
    assert not os.path.exists(converted_name)
    conv_cmd = get_conv_cmd(fullname, converted_name)
    self._exec(conv_cmd, fullname)
    assert os.path.exists(converted_name), f"could not convert file using the following command:\n\t{conv_cmd}"
    if not can_write_metadata(converted_name):
      send2trash(converted_name)
      assert False, f"bad conversion: metadata not writable"
    if not keep_original:
      send2trash(fullname)
    return converted_name

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
        print("\n"*16)

  def process_recent_files(self, n_interactive:int) -> None:
    buffer_files = []
    for f in os.listdir(self.cfg.buffer_dir):
      fullname = os.path.join(self.cfg.buffer_dir, f)
      if not os.path.isfile(fullname) or hlp.file_extension(fullname) in ['crdownload', 'part']:
        continue
      buffer_files.append(fullname)
    for fullname in sorted(buffer_files, key=os.path.getmtime, reverse=True):
      if n_interactive == 0:
        break
      n_interactive -= self.process_file(fullname)
      logging.info("Processing done.\n\n")

  def process_file(self, fullname) -> bool:
    logging.info("process_file '%s'", fullname)
    was_interactive = False

    if self.converter.needs_conversion(fullname):
      logging.info("Converting...")
      try:
        fullname = self.converter.convert(fullname, keep_original=False)
      except AssertionError as ex:
        logging.warning("Could not convert '%s', assertion error: %s", fullname, ex)
        logging.warning("Moving file to '%s'", self.cfg.uncateg_dir)
        shutil.move(fullname, self.cfg.uncateg_dir)
        return False

    conflict_fname = os.path.join(self.cfg.dest_dir, os.path.basename(fullname))
    if os.path.exists(conflict_fname):
      logging.error("File already exists:\n\t%s\n\t%s", conflict_fname, get_metadata(conflict_fname))
      hlp.start_file(conflict_fname)
      while True:
        usr_input = hlp.amnesic_input("Do you want to skip and remove the contender? [y/n]: ").lower()
        if usr_input in ["y", "yes"]:
          logging.info("Moving '%s' to trash", fullname)
          send2trash(fullname)
          return False
        elif usr_input in ["n", "no"]:
          logging.info("Ok, we'll just rename the file and continue")
          new_fullname = '_contend'.join(os.path.splitext(fullname))
          os.rename(fullname, new_fullname)
          return self.process_file(new_fullname)

    if not has_metadata(fullname):
      assert can_write_metadata(fullname), fullname
      self.gui.show_editor(fullname)
      was_interactive = True
    else:
      logging.info("File already has metadata:\n\t%s", get_metadata(fullname))

    if has_metadata(fullname):
      logging.info("Moving file to '%s'", self.cfg.dest_dir)
      shutil.move(fullname, self.cfg.dest_dir)
    else:
      logging.warning("At the end, still no metadata in %s", fullname)

    return was_interactive

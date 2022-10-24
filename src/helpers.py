import os
import sys
import subprocess


def truncate(s:str, lim:int, suffix:str='…') -> str:
  return s[:lim-len(suffix)]+suffix if len(s)>lim else s


def short_fname(fullname:str) -> str:
  return fullname.rsplit('/', maxsplit=1)[-1]


def file_extension(name:str) -> str:
  return name.rsplit('.', maxsplit=1)[-1].lower()


def start_file(fname:str) -> None:
  if sys.platform == "win32":
    os.startfile(fname)
  elif sys.platform == "darwin":
    subprocess.call(["open", fname])
  else:
    subprocess.call(["xdg-open", fname])

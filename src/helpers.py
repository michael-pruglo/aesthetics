def truncate(s:str, lim:int, suffix:str='…') -> str:
  return s[:lim-len(suffix)]+suffix if len(s)>lim else s

def short_fname(fullname:str):
  return fullname.rsplit('/', maxsplit=1)[-1]

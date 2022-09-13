def truncate(s:str, lim:int, suffix:str='…') -> str:
  return s[:lim-len(suffix)]+suffix if len(s)>lim else s


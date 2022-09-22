from typing import Callable


def truncate(s:str, lim:int, suffix:str='…') -> str:
  return s[:lim-len(suffix)]+suffix if len(s)>lim else s


def short_fname(fullname:str):
  return fullname.rsplit('/', maxsplit=1)[-1]


# https://www.rapidtables.com/convert/color/rgb-to-hsl.html
def rgb_to_hsl(r, g, b) -> tuple:
  r /= 255
  g /= 255
  b /= 255
  cmax = max(r,g,b)
  cmin = min(r,g,b)
  delta = cmax - cmin

  l = (cmax+cmin)/2

  if delta == 0:
    h = 0
  else:
    if cmax == r:
      h = (g-b)//delta%6
    elif cmax == g:
      h = (b-r)/delta+2
    elif cmax == b:
      h = (r-g)/delta+4
    h = int(h*60)

  s = 0 if delta==0 else delta/(1-abs(2*l-1))

  return h, s, l


def hsl_to_rgb(h, s, l) -> tuple:
  c = (1-abs(2*l-1)) * s
  x = c * (1-abs(h/60%2-1))
  m = l-c/2
  r,g,b = [(c,x,0),(x,c,0),(0,c,x),(0,x,c),(x,0,c),(c,0,x)][h//60]
  r = round((r+m)*255)
  g = round((g+m)*255)
  b = round((b+m)*255)
  return r,g,b


def hex_to_rgb(col:str) -> tuple:
  if len(col) == 4:
    col = '#' + ''.join([c*2 for c in col[1:]])
  assert len(col) == 7, col
  r,g,b = (int(col[i:i+2],16) for i in range(1,len(col)-1,2))
  return r,g,b


def rgb_to_hex(r,g,b) -> str:
  return '#' + ''.join([f"{v:02x}" for v in (r,g,b)])


def spice_up_color(
  colorstr:str,
  rgbop:Callable[[int,int,int],tuple]=None,
  hslop:Callable[[int,float,float],tuple]=None,
) -> str:
  rgb = hex_to_rgb(colorstr)
  if rgbop:
    rgb = rgbop(*rgb)
  hsl = rgb_to_hsl(*rgb)
  if hslop:
    hsl = hslop(*hsl)
  return rgb_to_hex(*hsl_to_rgb(*hsl))

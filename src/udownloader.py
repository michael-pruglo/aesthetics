import logging
import subprocess
import os
import shutil
import re
import glob
from enum import Enum, auto
from dataclasses import dataclass
import random
from abc import ABC, abstractmethod
from instaloader import Instaloader, Post

logging.basicConfig(level=logging.DEBUG)
SUPPORTED_FORMATS = ['jpg', 'mp4', 'gif', 'jfif', 'jpeg', 'png']

def is_direct_link(url:str) -> bool:
  pattern = r"\.(" + '|'.join(SUPPORTED_FORMATS) + r")(\?.+)?"
  return bool(re.search(pattern, url))

def parse_url(url:str) -> tuple:
  m = re.match(r"(?:https://)?(?:www\.)?(\w+)\.com([^?\s]+)(?:\?\S+)?", url)
  if not m:
    raise ValueError(f"cannot parse url '{url}'")
  return m[1], m[2]



class SiteDownloader(ABC):
  @abstractmethod
  def retrieve(self, url) -> str:
    pass


class UDownloader:
  def __init__(self, dst_path:str) -> None:
    self.dst_path = dst_path
    self.dls:dict[str,SiteDownloader] = {
      "instagram": IgDownloader(dst_path),
      # "youtube": self.download_youtube,
      # "tiktok": self.download_tiktok,
      # "reddit": self.download_reddit,
      # "twitter": self.download_twitter,
      # "pinterest": self.download_pinterest,
    }

  def retreive_media(self, url:str) -> str:
    """ download the media and return fullname of file on disk """
    if is_direct_link(url):
      return self.download_direct(url)
    else:
      domain, urlpath = parse_url(url)
      assert domain in self.dls
      return self.dls[domain].retrieve(urlpath)

  def download_direct(self, url:str) -> str:
    logging.debug("download direct ", url)
    # BAD BAD security! TODO: protect against injections
    output = subprocess.run([f'wget -nv -P {self.dst_path} {url} 2>&1'], shell=True, capture_output=True)
    fullname = output.stdout.decode().strip()
    logging.info("downloaded ", fullname, "    output:", fullname)
    return fullname


class IgDownloader(SiteDownloader):
  @dataclass
  class UrlData:
    class Type(Enum):
      POST = auto()
      STORY = auto()
    type: Type
    shortcode: str = None
    idx: int = None
    username: str = None
    story_id: int = None

  def __init__(self, dst_path) -> None:
    self.dst_path = dst_path
    self.L = None
    assert IgDownloader._parse_url_test()

  def retrieve(self, urlpath) -> str:
    logging.debug(f"ig retreive {urlpath}")
    if not self.L:
      self._init_l()

    urldata = self._parse_urlpath(urlpath)
    if urldata.type == IgDownloader.UrlData.Type.POST:
      self.retreive_post(urldata.shortcode, urldata.idx)
    elif urldata.type == IgDownloader.UrlData.Type.STORY:
      self.retreive_highlight(urldata.username, urldata.story_id, urldata.idx)
    else:
      raise RuntimeError(f"unknown urldata type: {urldata}")

  def retreive_post(self, shortcode:str, idx:int=None):
    """ Note idx is 0-indexed """
    tmppath = f"tmp_ig_{random.randint(1,1000000)}"
    os.mkdir(tmppath)

    post = Post.from_shortcode(self.L.context, shortcode)
    self.L.download_post(post, target=tmppath)

    sffx = f"*_{idx+1}.*" if idx else "*"
    cand_names = os.path.join(os.path.abspath(tmppath), sffx)
    cands = glob.glob(cand_names)
    logging.debug(f" cand_names = {cand_names}   cands = {cands}")
    ret_name = None
    assert len(cands) == 1
    fname = cands[0]
    logging.debug(f"copy {fname}")
    ret_name = shutil.copy(fname, self.dst_path)
    shutil.rmtree(tmppath, ignore_errors=False)

    return ret_name

  @staticmethod
  def _parse_urlpath(urlpath:str) -> UrlData:
    m = re.match(r"/?p/(\w+)(?:/(\d+))?/?", urlpath)
    if m:
      return IgDownloader.UrlData(
        type=IgDownloader.UrlData.Type.POST,
        shortcode=m[1],
        idx=int(m[2]) if m[2] else None,
      )

    m = re.match(r"/?stories/(\w+)/(\d+)(?:/(\d+))?/?", urlpath)
    if m:
      return IgDownloader.UrlData(
        type=IgDownloader.UrlData.Type.STORY,
        username=m[1],
        story_id=int(m[2]),
        idx=int(m[3]) if m[3] else None,
      )

    raise ValueError(f"cannot parse urlpath '{urlpath}'")

  def _init_l(self):
    self.L = Instaloader(
      user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 244.0.0.12.112",
      filename_pattern="{profile}_{shortcode}",
      download_video_thumbnails=False,
      save_metadata=False,
      post_metadata_txt_pattern="",
    )
    self.L.login("", "")
    logging.debug("_init_l success")

  @staticmethod
  def _parse_url_test():
    for urlpath, exp in [
      ( "p/SHRTCDE/4", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="SHRTCDE", idx=4)),
      ( "p/SHRTCDE", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="SHRTCDE", idx=None)),
      ( "stories/lexfridman/2972926188754278171/2", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.STORY, username="lexfridman", story_id=2972926188754278171, idx=2)),
      ( "stories/lexfridman/2972926188754278171", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.STORY, username="lexfridman", story_id=2972926188754278171, idx=None)),
    ]:
      for pref in ["", "/"]:
        for suff in ["", "/"]:
          given = IgDownloader._parse_urlpath(pref + urlpath + suff)
          assert given == exp, f"\n\t{pref+urlpath+suff}\n\t{given}"
    return True

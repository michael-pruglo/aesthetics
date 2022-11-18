import logging
import subprocess
import os
import shutil
import re
import glob
import itertools
import urllib.request
from enum import Enum, auto
from dataclasses import dataclass
from abc import ABC, abstractmethod
from instaloader import Instaloader, Post, Profile


SUPPORTED_FORMATS = ['jpg', 'mp4', 'gif', 'jfif', 'jpeg', 'png']

def get_direct_fname(url:str) -> str:
  pattern = r"/(\w+\.(?:" + '|'.join(SUPPORTED_FORMATS) + r"))(\?.+)?"
  m = re.search(pattern, url)
  return m[1] if m else ""

def parse_url(url:str) -> tuple:
  m = re.match(r"(?:https://)?(?:www\.)?(\w+)\.com([^?\s]+)(?:\?\S+)?", url)
  if not m:
    raise ValueError(f"cannot parse url '{url}'")
  return m[1], m[2]



class SiteDownloader(ABC):
  @abstractmethod
  def retrieve(self, url) -> str:
    pass


@dataclass
class UDownloaderCfg:
  dst_path: str
  ig_login: str
  ig_password: str


class UDownloader:
  def __init__(self, cfg:UDownloaderCfg) -> None:
    assert os.path.exists(cfg.dst_path), "did you forget to mount it?"
    self.dst_path = cfg.dst_path
    self.dls:dict[str,SiteDownloader] = {
      "instagram": IgDownloader(cfg.dst_path, cfg.ig_login, cfg.ig_password),
      # "youtube": self.download_youtube,
      # "tiktok": self.download_tiktok,
      # "reddit": self.download_reddit,
      # "twitter": self.download_twitter,
      # "pinterest": self.download_pinterest,
    }
    logging.basicConfig(level=logging.DEBUG)

  def retreive_media(self, url:str) -> str:
    """ download the media and return fullname of file on disk """
    if (direct_fname:=get_direct_fname(url)):
      return self.download_direct(url, direct_fname)
    else:
      domain, urlpath = parse_url(url)
      assert domain in self.dls
      return self.dls[domain].retrieve(urlpath)

  def download_direct(self, url:str, fname:str) -> str:
    logging.debug("download direct '%s'", url)
    fullname = os.path.join(self.dst_path, fname)
    urllib.request.urlretrieve(url, filename=fullname)
    logging.info("downloaded fname '%s'", fullname)
    return fullname


class IgDownloader(SiteDownloader):
  @dataclass
  class UrlData:
    class Type(Enum):
      POST = auto()
      HIGHLIGHT = auto()
      STORY = auto()
    type: Type
    shortcode: str = None
    idx: int = None  # NOTE: 0-indexed
    username: str = None
    story_id: int = None

  def __init__(self, dst_path:str, ig_login:str, ig_password:str) -> None:
    self.dst_path = dst_path
    self.ig_login = ig_login
    self.ig_password = ig_password
    self.L = None
    assert IgDownloader._parse_url_test()

  def retrieve(self, urlpath) -> str:
    logging.debug("ig retreive %s", urlpath)
    if not self.L:
      self._init_l()

    urldata = self._parse_urlpath(urlpath)
    if urldata.type == IgDownloader.UrlData.Type.POST:
      return self.retreive_post(urldata.shortcode, urldata.idx)
    elif urldata.type == IgDownloader.UrlData.Type.HIGHLIGHT:
      return self.retreive_highlight(urldata.username, urldata.story_id, urldata.idx)
    elif urldata.type == IgDownloader.UrlData.Type.STORY:
      return self.retreive_story(urldata.username, urldata.story_id)
    else:
      raise RuntimeError(f"unknown urldata type: {urldata}")

  def retreive_post(self, shortcode:str, idx:int=None) -> str:
    tmppath = f"tmp_ig_{shortcode}"
    if not os.path.exists(tmppath):
      os.mkdir(tmppath)

    post = Post.from_shortcode(self.L.context, shortcode)
    self.L.download_post(post, target=tmppath)

    sffx = f"*_{idx+1}.*" if idx is not None else "*"
    cand_names = os.path.join(os.path.abspath(tmppath), sffx)
    cands = glob.glob(cand_names)
    logging.debug(" cand_names = %s   cands = %s", str(cand_names), str(cands))
    ret_name = None
    assert len(cands) == 1
    fname = cands[0]
    logging.debug("copy %s", fname)
    ret_name = shutil.copy(fname, self.dst_path)
    shutil.rmtree(tmppath, ignore_errors=False)

    return ret_name

  def retreive_highlight(self, username:str, highlight_id:int, idx:int) -> str:
    tmppath = f"tmp_ig_{highlight_id}"
    if not os.path.exists(tmppath):
      os.mkdir(tmppath)

    user = Profile.from_username(self.L.context, username)
    highlight = next(h for h in self.L.get_highlights(user) if h.unique_id==highlight_id)
    idx = highlight.itemcount - 1 - idx  # api returns them in reversed (chronological) order
    item = next(itertools.islice(highlight.get_items(), idx, idx+1))
    self.L.download_storyitem(item, tmppath)

    sffx = "*"
    cand_names = os.path.join(os.path.abspath(tmppath), sffx)
    cands = glob.glob(cand_names)
    logging.debug(" cand_names = %s   cands = %s", str(cand_names), str(cands))
    ret_name = None
    assert len(cands) == 1
    fname = cands[0]
    logging.debug("copy %s", fname)
    ret_name = shutil.copy(fname, self.dst_path)
    shutil.rmtree(tmppath, ignore_errors=False)

    return ret_name

  def retreive_story(self, username:str, story_id:int) -> str:
    tmppath = f"tmp_ig_{story_id}"
    if not os.path.exists(tmppath):
      os.mkdir(tmppath)

    user = Profile.from_username(self.L.context, username)
    item = next(it
                for story in self.L.get_stories([user.userid])
                for it in story.get_items()
                if it.mediaid==story_id)
    self.L.download_storyitem(item, tmppath)

    sffx = "*"
    cand_names = os.path.join(os.path.abspath(tmppath), sffx)
    cands = glob.glob(cand_names)
    logging.debug(" cand_names = %s   cands = %s", str(cand_names), str(cands))
    ret_name = None
    assert len(cands) == 1
    fname = cands[0]
    logging.debug("copy %s", fname)
    ret_name = shutil.copy(fname, self.dst_path)
    shutil.rmtree(tmppath, ignore_errors=False)

    return ret_name

  @staticmethod
  def _parse_urlpath(urlpath:str) -> UrlData:
    m = re.match(r"/?p/([\w-]+)(?:/(\d+))?/?", urlpath)
    if m:
      shcode = m[1]
      if len(shcode) != 11:
        logging.warning("ig shortcode '%s' length != 11", shcode)
      if shcode[0] != 'C':
        logging.warning("ig shortcode '%s' doesn't stars with 'C'", shcode)
      return IgDownloader.UrlData(
        type=IgDownloader.UrlData.Type.POST,
        shortcode=shcode,
        idx=int(m[2]) if m[2] else None,
      )

    # NOTE: in case of highlights, user needs to manually type username at the end
    # e.g. intead of      'instagram.com/stories/highlights/18151027342237295/1/',
    # user needs to input 'instagram.com/stories/highlights/18151027342237295/1/joerogan'
    # this is because there's no way to download without username or deduce it from id
    m = re.match(r"/?stories/highlights/(\d+)/(\d+)/(\w+)/?", urlpath)
    if m:
      return IgDownloader.UrlData(
        type=IgDownloader.UrlData.Type.HIGHLIGHT,
        story_id=int(m[1]),
        idx=int(m[2]),
        username=m[3],
      )

    m = re.match(r"/?stories/(\w+)/(\d+)/?", urlpath)
    if m:
      assert m[1] != "highlights", "did you forget to manually type name for highlight?"
      return IgDownloader.UrlData(
        type=IgDownloader.UrlData.Type.STORY,
        username=m[1],
        story_id=int(m[2]),
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
    try:
      self.L.load_session_from_file(self.ig_login)
      logging.info("loaded session from file")
    except FileNotFoundError:
      logging.info("needs a fresh login")
      self.L.login(self.ig_login, self.ig_password)
      self.L.save_session_to_file()
    except Exception:
      logging.exception("")

  @staticmethod
  def _parse_url_test():
    for urlpath, exp in [
      ( "p/SHRTCDE/4", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="SHRTCDE", idx=4)),
      ( "p/with-dash/3", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="with-dash", idx=3)),
      ( "p/SHRTCDE", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="SHRTCDE", idx=None)),
      ( "stories/lexfridman/2972926188754278171", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.STORY, username="lexfridman", story_id=2972926188754278171)),
      ( "stories/highlights/18151027342237295/3/joerogan", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.HIGHLIGHT, username="joerogan", story_id=18151027342237295, idx=3)),
    ]:
      for pref in ["", "/"]:
        for suff in ["", "/"]:
          given = IgDownloader._parse_urlpath(pref + urlpath + suff)
          assert given == exp, f"\n\t{pref+urlpath+suff}\n\t{given}"
    return True

import logging
import random
import shutil
import os
import glob
import re
import itertools
from enum import Enum, auto
from dataclasses import dataclass
from instaloader import Instaloader, Post, Profile

from down_types import SiteDownloader


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

    self.tmppath = f"tmp_ig_{random.randint(2000,10000000)}"
    if not os.path.exists(self.tmppath):
      os.mkdir(self.tmppath)

    urldata = self._parse_urlpath(urlpath)
    if urldata.type == IgDownloader.UrlData.Type.POST:
      sffx = self.retreive_post(urldata.shortcode, urldata.idx)
    elif urldata.type == IgDownloader.UrlData.Type.HIGHLIGHT:
      sffx = self.retreive_highlight(urldata.username, urldata.story_id, urldata.idx)
    elif urldata.type == IgDownloader.UrlData.Type.STORY:
      sffx = self.retreive_story(urldata.username, urldata.story_id)
    else:
      raise RuntimeError(f"unknown urldata type: {urldata}")

    cand_names = os.path.join(os.path.abspath(self.tmppath), sffx)
    cands = glob.glob(cand_names)
    logging.debug(" cand_names = %s   cands = %s", str(cand_names), str(cands))
    assert len(cands) == 1
    fname = cands[0]
    ret_name = shutil.copy(fname, self.dst_path)
    shutil.rmtree(self.tmppath, ignore_errors=False)
    return ret_name

  def retreive_post(self, shortcode:str, idx:int=None) -> str:
    post = Post.from_shortcode(self.L.context, shortcode)
    if idx is not None:
      self.L.slide_start = self.L.slide_end = idx
    self.L.download_post(post, target=self.tmppath)
    return "*"
    # return f"*_{idx+1}.*" if idx is not None else "*"

  def retreive_highlight(self, username:str, highlight_id:int, idx:int) -> str:
    user = Profile.from_username(self.L.context, username)
    highlight = next(h for h in self.L.get_highlights(user) if h.unique_id==highlight_id)
    idx = highlight.itemcount - 1 - idx  # api returns them in reversed (chronological) order
    item = next(itertools.islice(highlight.get_items(), idx, idx+1))
    self.L.download_storyitem(item, self.tmppath)
    return "*"

  def retreive_story(self, username:str, story_id:int) -> str:
    user = Profile.from_username(self.L.context, username)
    item = next(it
                for story in self.L.get_stories([user.userid])
                for it in story.get_items()
                if it.mediaid==story_id)
    self.L.download_storyitem(item, self.tmppath)
    return "*"

  @staticmethod
  def _parse_urlpath(urlpath:str) -> UrlData:
    m = re.match(r"/?p/([\w-]+)(?:/(\d+))?/?", urlpath)
    if m:
      shcode = m[1]
      if len(shcode) != 11:
        logging.warning("ig shortcode '%s' length != 11", shcode)
      if shcode[0] not in 'BC':
        logging.warning("ig shortcode '%s' doesn't start with any of 'BC'", shcode)
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
      ( "p/C_SHRTCDE12/4", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="C_SHRTCDE12", idx=4)),
      ( "p/C_with-dash/3", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="C_with-dash", idx=3)),
      ( "p/C_SHRTCDE12", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.POST, shortcode="C_SHRTCDE12", idx=None)),
      ( "stories/lexfridman/2972926188754278171", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.STORY, username="lexfridman", story_id=2972926188754278171)),
      ( "stories/highlights/18151027342237295/3/joerogan", IgDownloader.UrlData(type=IgDownloader.UrlData.Type.HIGHLIGHT, username="joerogan", story_id=18151027342237295, idx=3)),
    ]:
      for pref in ["", "/"]:
        for suff in ["", "/"]:
          given = IgDownloader._parse_urlpath(pref + urlpath + suff)
          assert given == exp, f"\n\t{pref+urlpath+suff}\n\t{given}"
    return True

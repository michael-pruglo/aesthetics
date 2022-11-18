import logging
import os
import re
import urllib.request

from down_types import UDownloaderCfg, SiteDownloader
from down_ig import IgDownloader


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

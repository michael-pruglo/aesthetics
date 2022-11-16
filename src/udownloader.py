import subprocess
import re
from instaloader import Instaloader, Post

SUPPORTED_FORMATS = ['jpg', 'mp4', 'gif', 'jfif', 'jpeg', 'png']

def is_direct_link(url:str) -> bool:
  pattern = r"\.(" + '|'.join(SUPPORTED_FORMATS) + r")(\?.+)?"
  return bool(re.search(pattern, url))

def get_host(url:str) -> str:
  if "youtu.be" in url:
    return "youtube"
  m = re.search(r"([a-z]+)\.com/", url)
  assert m
  return m[1]


class UDownloader:
  def __init__(self, dst_path:str) -> None:
    self.dst_path = dst_path
    self.instldr = None

  def retreive_media(self, url:str) -> str:
    """ download the media and return fullname of file on disk """
    if is_direct_link(url):
      return self.download_direct(url)
    else:
      downloader_f = {
        "instagram": self.download_instagram,
        "youtube": self.download_youtube,
        "tiktok": self.download_tiktok,
        "reddit": self.download_reddit,
        "twitter": self.download_twitter,
        "pinterest": self.download_pinterest,
      }[get_host(url)]
      return downloader_f(url)
      # return os.path.join(dst_path, "006f129e1d4baaa9cd5e766d06256f58.jpg")

  def download_direct(self, url:str) -> str:
    print("download direct ", url)
    # BAD BAD security! TODO: protect against injections
    output = subprocess.run([f'wget -nv -P {self.dst_path} {url} 2>&1'], shell=True, capture_output=True)
    fullname = output.stdout.decode().strip()
    print("downloaded ", fullname, "    output:", output.stdout.decode())
    return fullname

  def download_instagram(self, url:str):
    if not self.instldr:
      self.instldr = Instaloader(
          user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 244.0.0.12.112",
          filename_pattern="{profile}_{shortcode}",
          download_video_thumbnails=False,
          save_metadata=False,
      )
      self.instldr.load_session_from_file('sonderishere')


class SiteLoader:
  pass


class IgLoader(SiteLoader):
  pass

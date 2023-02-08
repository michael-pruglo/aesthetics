import logging
import os
import yt_dlp

import helpers as hlp
from down_types import UDownloaderCfg


class UDownloader:
  def __init__(self, cfg:UDownloaderCfg) -> None:
    assert os.path.exists(cfg.dir_ready), "did you forget to mount it?"
    self.cfg = cfg

  def retreive_media(self, url:str) -> str:
    """ download the media and return fullname of file on disk """
    PARANOID = True
    if PARANOID:
      # dry run
      with yt_dlp.YoutubeDL({"listformats":True}) as ydl:
        try:
          ydl.download(url)
        except yt_dlp.utils.DownloadError as e:
          logging.error("yt-dlp cannot download '%s'\n%s", url, e)
          raise

      # usr confirmation
      if hlp.amnesic_input("proceed? ") == "n":
        return ""

    # real download run
    ret_name = None
    def monitor_name(d):
      nonlocal ret_name
      if d['status'] == 'finished':
        ret_name = d.get('info_dict').get('_filename')

    dwnl_opts = {
      "restrictfilenames": True,
      # "usenetrc": True,  # yt-dlp does not authenticate IG properly
      "windowsfilenames": True,
      "paths": {'home': self.cfg.dir_ready},
      "progress_hooks": [monitor_name],
    }
    with yt_dlp.YoutubeDL(dwnl_opts) as ydl:
      ydl.download([url])

    return ret_name

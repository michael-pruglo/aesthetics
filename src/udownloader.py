import os

class UDownloader:
  # download the media and return fullname of file on disk
  def retreive_media(url:str, dst_path:str) -> str:
    fname = "006f129e1d4baaa9cd5e766d06256f58.jpg"
    fullname = os.path.join(dst_path, fname)
    return fullname

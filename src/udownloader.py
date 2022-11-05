import subprocess


class UDownloader:
  SUPPORTED_FORMATS = ['.jpg', '.mp4', '.gif', '.jfif', '.jpeg', '.png']

  @staticmethod
  def retreive_media(url:str, dst_path:str) -> str:
    """ download the media and return fullname of file on disk """
    if UDownloader.is_direct_link(url):
      return UDownloader.download_direct(url, dst_path)
    else:
      downloader_f = {
        "youtube": UDownloader.download_youtube,
        "tiktok": UDownloader.download_tiktok,
        "instagram": UDownloader.download_instagram,
        "reddit": UDownloader.download_reddit,
        "twitter": UDownloader.download_twitter,
        "pinterest": UDownloader.download_pinterest,
      }[UDownloader.get_host(url)]
      return downloader_f(url, dst_path)
      # return os.path.join(dst_path, "006f129e1d4baaa9cd5e766d06256f58.jpg")

  @staticmethod
  def is_direct_link(url:str) -> bool:
    return url.endswith(tuple(UDownloader.SUPPORTED_FORMATS))

  @staticmethod
  def download_direct(url:str, dst_path:str) -> str:
    print("download direct ", url)
    # BAD BAD security! TODO: protect against injections
    output = subprocess.run([f'wget -nv -P {dst_path} {url} 2>&1 | cut -d\\" -f2'], shell=True, capture_output=True)
    fullname = output.stdout.decode().strip()
    print("downloaded ", fullname)
    return fullname

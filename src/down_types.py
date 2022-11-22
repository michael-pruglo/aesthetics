from dataclasses import dataclass
from abc import ABC, abstractmethod


class SiteDownloader(ABC):
  @abstractmethod
  def retrieve(self, url) -> str:
    pass


@dataclass
class UDownloaderCfg:
  dir_main: str
  dir_ready: str
  dir_uncateg: str
  ig_login: str
  ig_password: str

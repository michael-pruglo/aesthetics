from dataclasses import dataclass
from abc import ABC, abstractmethod


class SiteDownloader(ABC):
  @abstractmethod
  def retrieve(self, url) -> str:
    pass


@dataclass
class UDownloaderCfg:
  dst_path: str
  ig_login: str
  ig_password: str

import unittest

from src.udownloader import is_direct_link, get_host


def all_variations(url:str):
  return [url, "www."+url, "https://www."+url]


class TestDownloader(unittest.TestCase):
  def test_is_direct_link(self):
    for url in [
      "scontent-sof1-2.cdninstagram.com/v/t51.2885-15/315614078_459966119577814_5720271647921337363_n.jpg?stp=dst-jpg_e35&_nc_ht=scontent-sof1-2.cdninstagram.com&_nc_cat=110&_nc_ohc=FuXCjCpiGdEAX8nyP7C&tn=rAi_JhHkptTxRq-B&edm=ALQROFkBAAAA&ccb=7-5&ig_cache_key=Mjk3MjgzODQ5NDA3OTMyMDEzMA%3D%3D.2-ccb7-5&oh=00_AfDbdPKvpZjGE5OMjaL6mCeY7xHiqGl44wbng-6TGYlSaw&oe=6379C7C3&_nc_sid=30a2ef",
      "i.imgur.com/PaI3Yyy.jpeg",
    ]:
      for fullurl in all_variations(url):
        self.assertTrue(is_direct_link(fullurl), fullurl)

    for url in [
      "instagram.com/p/ClBpN0sty75/",
      "imgur.com/gallery/g5SCM9C",
    ]:
      for fullurl in all_variations(url):
        self.assertFalse(is_direct_link(fullurl), fullurl)

  def test_get_host(self):
    for url, host in [
      ("instagram.com/p/ClBpN0sty75/", "instagram"),
    ]:
      for fullurl in all_variations(url):
        self.assertEqual(get_host(fullurl), host, fullurl)

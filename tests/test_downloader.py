import unittest

from src.udownloader import is_direct_link, parse_url


def all_variations(url:str):
  prefs = ["", "www.", "https://", "https://www."]
  suffs = ["", "?blah=value&blah2=foo"]
  return [p+url+s for p in prefs for s in suffs]


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

  def test_parse_url(self):
    for url, domain, urlpath in [
      ("instagram.com/p/ClBpN0sty75/", "instagram", "/p/ClBpN0sty75/"),
      ("instagram.com/p/ClBpN0sty75/3/", "instagram", "/p/ClBpN0sty75/3/"),
      ("instagram.com/stories/lexfridman/2972926188754278171/", "instagram", "/stories/lexfridman/2972926188754278171/"),
      ("instagram.com/stories/lexfridman/2972926188754278171/2/", "instagram", "/stories/lexfridman/2972926188754278171/2/"),
      ("instagram.com/stories/highlights/18151027342237295/", "instagram", "/stories/highlights/18151027342237295/"),
      ("instagram.com/stories/highlights/18151027342237295/4/", "instagram", "/stories/highlights/18151027342237295/4/"),
    ]:
      for fullurl in all_variations(url):
        self.assertTupleEqual(parse_url(fullurl), (domain,urlpath), fullurl)

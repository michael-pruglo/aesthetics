import os

from ai_backend_tags import ConvnextTiny
from ai_backend_stars import StarPredictorBaseline
import helpers as hlp
from metadata import get_metadata


class Assistant:
  def __init__(self):
    try:
      self.tags_backend = ConvnextTiny()
    except:
      self.tags_backend = None
    self.stars_backend = StarPredictorBaseline()

  def suggest_tags(self, fname:str, visual=False) -> list[str]:
    if not self.tags_backend:
      return []
    return self.tags_backend.suggest_tags(os.path.abspath(fname))[:20]

  def predict_rating(self, fname:str) -> float:
    return self.stars_backend.predict_from_tags(get_metadata(fname)[0])


if __name__ == "__main__":
  assistant = Assistant()
  folder = "./sample_imgs/"
  for f in os.listdir(folder):
    fname = os.path.join(folder, f)
    tags, stars = get_metadata(fname)
    print(f"\n\nactual metadata: {stars} {tags}\n"
          f"suggested stars: {assistant.predict_rating(fname)}\n"
          f"suggested tags:{assistant.suggest_tags(fname)}\n")

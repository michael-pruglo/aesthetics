import os
import numpy as np
import matplotlib.pyplot as plt

from ai_backend_tags import ConvnextTiny
from ai_backend_stars import RandomForest
import helpers as hlp
from metadata import get_metadata


class Assistant:
  def __init__(self):
    self.tags_backend = ConvnextTiny()
    self.stars_backend = RandomForest()

  def suggest_tags(self, fname:str) -> list[str]:
    suggestion = self.tags_backend.suggest_tags(os.path.abspath(fname))[:20]
    tags = [tag for tag,_ in suggestion]
    suggested_tags = [tag for tag,prob in suggestion if prob>=0.5]
    probs = [prob for _,prob in suggestion]

    hlp.start_file(fname)

    plt.figure(f"suggested tags for {hlp.short_fname(fname)}", figsize=(10,5))
    plt.barh(tags[::-1], probs[::-1])
    plt.subplots_adjust(left=0.25)
    plt.xticks(np.linspace(0, 1, 11))
    plt.grid(visible=True, axis='x')
    plt.margins(y=0)
    plt.xlim(0,1)
    plt.show()

    return suggested_tags

  def predict_rating(self, fname:str) -> float:
    return self.stars_backend.predict_from_tags([tags])


if __name__ == "__main__":
  assistant = Assistant()
  folder = "./sample_imgs/"
  for f in os.listdir(folder):
    fname = os.path.join(folder, f)
    tags, stars = get_metadata(fname)
    print(f"\n\nactual metadata: {stars} {tags}\n"
          f"suggested stars: {assistant.predict_rating(fname)}\n"
          f"suggested tags:{assistant.suggest_tags(fname)}\n")

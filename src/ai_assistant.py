from fastai.vision.all import *
import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

import helpers as hlp


class Assistant:
  def __init__(self):
    saved_model = os.path.abspath("./models/convnext_tiny_in22k_new.pkl")
    self.tag_learner = load_learner(saved_model)

  def suggest_tags(self, fname:str) -> list[str]:
    tags, booltensor, probs = self.tag_learner.predict(os.path.abspath(fname))

    msg = f"suggested tags for {hlp.short_fname(fname)} "
    print(msg, tags)

    with Image.open(fname) as im:
      im.show()

    data = sorted(zip(probs, self.tag_learner.dls.vocab))[-20:]
    plt.figure(msg, figsize=(10,5))
    plt.barh([t[1] for t in data], [t[0] for t in data])
    plt.subplots_adjust(left=0.25)
    plt.xticks(np.linspace(0, 1, 11))
    plt.grid(visible=True, axis='x')
    plt.margins(y=0)
    plt.xlim(0,1)
    plt.show()

    return tags

  def predict_rating(slef, fname:str) -> float:
    pass


if __name__ == "__main__":
  Assistant().suggest_tags("./sample_imgs/006f129e1d4baaa9cd5e766d06256f58.jpg")

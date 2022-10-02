import os
from fastai.vision.all import load_learner

from ai_types import TagsBackend


class ConvnextTiny(TagsBackend):
  def __init__(self):
    super().__init__()
    saved_model = os.path.abspath("./models/convnext_tiny_in22k_new.pkl")
    self.learner = load_learner(saved_model)

  def suggest_tags(self, fullname):
    tags, booltensor, probs = self.learner.predict(fullname)
    return sorted(zip(self.learner.dls.vocab, probs), key=lambda t:t[1], reverse=True)

from abc import ABC, abstractmethod


class TagsBackend(ABC):
  @abstractmethod
  def suggest_tags(self, fullname:str) -> list[tuple[str,float]]:
    """return list of tuples (tag, probability)"""
    pass


class StarPredictorBackend(ABC):
  @abstractmethod
  def predict_from_tags(self, tags:list[str]) -> float:
    pass

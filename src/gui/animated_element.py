from abc import ABC, abstractmethod
from tkinter import Misc


class AnimElement(ABC):
  @abstractmethod
  def anim_update(self): pass

  @abstractmethod
  def anim_pause(self): pass

  @abstractmethod
  def anim_unpause(self): pass


class AnimElementsManager:
  def __init__(self, root:Misc, elements:list[AnimElement]=None) -> None:
    self.root = root
    self.elems = elements or []
    self.job_id = ""
    self.root.bind('<FocusOut>', self._on_focus_event)
    self.root.bind('<FocusIn>', self._on_focus_event)

  def _on_focus_event(self, event):
    if event.widget != self.root:
      return  # TODO: investigate why .!entry focusin triggers this handler
    for f in self.elems:
      if "out" in str(event).lower():
        f.anim_pause()
      else:
        f.anim_unpause()

  def add_element(self, element:AnimElement) -> None:
    self.elems.append(element)

  def run(self) -> None:
    for f in self.elems:
      f.anim_update()
    MAX_FPS = 90
    self.job_id = self.root.after(int(1000/MAX_FPS), self.run)

  def stop(self) -> None:
    if self.job_id:
      self.root.after_cancel(self.job_id)
      self.job_id = ""

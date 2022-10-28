import os
import random
import unittest

from ae_rater_types import ProfileInfo, RatChange, Rating, UserListener
from ae_rater_view import RaterGui
from tests.helpers import MEDIA_FOLDER, SKIPLONG, get_initial_mediafiles


def generate_profiles(n:int) -> list[ProfileInfo]:
  def gen_one_prof(i, shname):
    return ProfileInfo(
      tags=f"gen{i}tgs",
      fullname=os.path.join(MEDIA_FOLDER, shname),
      stars=random.randint(0,500)/100,
      ratings={
        'ELO':Rating(random.randint(1000,2000),0),
        'Glicko':Rating(random.randint(1400,3000),random.randint(30,300))
      },
      nmatches=random.randint(2,100)
    )

  return [gen_one_prof(i, shname)
    for i,shname in zip(range(n), get_initial_mediafiles())
    if not shname.endswith((".mp4",".gif"))  # tkVideo needs mainloop with events
  ]

def generate_ratchange(n:int) -> list[RatChange]:
  return [RatChange(
            new_rating=Rating(random.randint(1000,3000),random.randint(30,300)),
            delta_rating=random.randint(-300,300),
            new_stars=random.randint(0,500)/100,
          )
          for _ in range(n)]


class MockListener(UserListener):
  def consume_result(self, *args, **kwargs): pass
  def give_boost(self, *args, **kwargs): pass
  def start_next_match(self): pass
  def update_meta(self, *args, **kwargs): pass
  def suggest_tags(self, *args, **kwargs): pass
  def give_awards(self, *args, **kwargs): pass
  def search_for(self, *args, **kwargs): return []


def can_create_window() -> bool:
  try:
    gui = RaterGui(MockListener(), ["a","b","c"])
    gui.root.destroy()
    return True
  except Exception as e:
    print("Cannot create gui:", e)
    return False


@unittest.skipIf(*SKIPLONG)
@unittest.skipUnless(can_create_window(), "cannot create tk interface")
class TestView(unittest.TestCase):
  def _test_competition_window(self, n:int):
    gui = RaterGui(MockListener(), ["a","b","c"])
    ldbrd = generate_profiles(random.randint(10,6000))
    for _ in range(10):
      participants = random.sample(ldbrd, n)
      gui.display_match(participants)
      gui.display_leaderboard(ldbrd, participants)
      gui.root.update()
      opinions = {sname:generate_ratchange(n) for sname in ['ELO','Glicko']}
      gui.conclude_match(opinions)
      gui.root.update()
      for id in gui.scheduled_jobs:
        gui.root.after_cancel(id)
    gui.root.destroy()

  def test_gui(self):
    for n in [2,10] + random.sample(range(3,13),2):
      self._test_competition_window(n)

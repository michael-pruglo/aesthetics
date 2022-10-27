#!/usr/bin/env python3

import os
import sys
import logging
from enum import Enum, auto

from helpers import short_fname
from ae_rater_types import Outcome, UserListener
from ae_rater_view import RaterGui
from ae_rater_model import RatingCompetition
from ai_assistant import Assistant


def setup_logger(log_filename):
  print(f"logging to file {log_filename}")

  logging.basicConfig(
    handlers = [
      logging.StreamHandler(),
      logging.FileHandler(log_filename, encoding="utf-8")
    ],
    format = "%(created)d %(message)s",
    level = logging.INFO
  )
  logging.info("Starting new session...")


class App(UserListener):
  class Mode(Enum):
    MATCH = auto()
    SEARCH = auto()

  def __init__(self, media_dir:str, mode:Mode=Mode.MATCH):
    self.model = RatingCompetition(media_dir, refresh=False)
    self.gui = RaterGui(self, self.model.get_tags_vocab())
    self.mode = mode
    self.ai_assistant = Assistant()
    self.num_participants = 2

  def run(self, num_participants:int) -> None:
    self.num_participants = num_participants
    try:
      if self.mode == App.Mode.MATCH:
        self.start_next_match()
      elif self.mode == App.Mode.SEARCH:
        self.show_search_results("")
      else:
        raise RuntimeError(f"cannot start mode {self.mode}")

      self.gui.mainloop()
    except Exception:
      logging.exception("")
    finally:
      self.model.on_exit()

  def consume_result(self, outcome:Outcome) -> None:
    participants = self.model.get_curr_match()  # needs to be before model.consume_result()
    rating_opinions = self.model.consume_result(outcome)
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants, outcome)
    self.gui.conclude_match(rating_opinions)

  def start_next_match(self) -> None:
    participants = self.model.generate_match(self.num_participants)
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants)
    self.gui.display_match(participants)

  def show_search_results(self, query:str) -> None:
    res = self.model.get_search_results(query)
    ldbrd = self.model.get_leaderboard()
    self.gui.display_leaderboard(ldbrd, res)
    self.gui.display_search(res)

  def give_boost(self, short_name:str, mult:int=1) -> None:
    self.model.give_boost(short_name, mult)
    self._refresh_gui()

  def update_meta(self, fullname:str, tags:list[str]=None, stars:int=None) -> None:
    self.model.update_meta(fullname, tags, stars)
    self._refresh_gui()

  def give_awards(self, fullname:str, awards:list[str]) -> None:
    self.model.give_awards(fullname, awards)

  def suggest_tags(self, fullname: str) -> list:
    return self.ai_assistant.suggest_tags(fullname)

  def _refresh_gui(self):
      updated_prof = self.model.get_curr_match()
      self.gui.display_leaderboard(self.model.get_leaderboard(), updated_prof)
      self.gui.display_match(updated_prof)


if __name__ == "__main__":
  given_dir = sys.argv[1] if len(sys.argv)>1 else "./sample_imgs/"
  given_dir = os.path.abspath(given_dir)
  assert os.path.exists(given_dir), f"path {given_dir} doesn't exist, maybe not mounted?"

  num_participants = int(sys.argv[2]) if len(sys.argv)>2 else 2
  # TODO: argparse to accept REFRESH and MODE
  setup_logger(log_filename=f"./logs/matches_{short_fname(given_dir)}.log")
  App(given_dir, App.Mode.SEARCH).run(num_participants)

#!/usr/bin/env python3

import os
import logging
import argparse

from helpers import short_fname
from ae_rater_types import AppMode, ManualMetadata, Outcome, UserListener
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
  def __init__(self, media_dir:str, mode:AppMode=AppMode.MATCH):
    self.model = RatingCompetition(media_dir, refresh=False)
    self.gui = RaterGui(self, self.model.get_tags_vocab(), mode)
    self.mode = mode
    self.ai_assistant = Assistant()
    self.num_participants = 2

  def run(self, num_participants:int) -> None:
    self.num_participants = num_participants
    try:
      if self.mode == AppMode.MATCH:
        self.start_next_match()
      elif self.mode == AppMode.SEARCH:
        self.search_for("")
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

  def search_for(self, query:str) -> None:
    N = 10
    res = self.model.get_search_results(query)[:N]
    ldbrd = self.model.get_leaderboard()
    self.gui.display_leaderboard(ldbrd, res)
    self.gui.display_match(res, N)

  def give_boost(self, short_name:str, mult:int=1) -> None:
    self.model.give_boost(short_name, mult)
    self._refresh_gui()

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    self.model.update_meta(fullname, meta)
    self._refresh_gui()

  def suggest_tags(self, fullname: str) -> list:
    return self.ai_assistant.suggest_tags(fullname)

  def _refresh_gui(self):
      updated_prof = self.model.get_curr_match()
      self.gui.display_leaderboard(self.model.get_leaderboard(), updated_prof)
      self.gui.display_match(updated_prof)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--search', dest='mode', action='store_const',
                      const=AppMode.SEARCH, default=AppMode.MATCH,
                      help="run SEARCH instead of MATCH mode")
  parser.add_argument('media_dir', nargs='?', default="./sample_imgs/",
                      help="media folder to operate on")
  parser.add_argument('num_participants', type=int, nargs='?', default=2,
                      help="number of participants in MATCH mode")
  # TODO: add -r for Refresh
  args = parser.parse_args()

  assert os.path.exists(args.media_dir), f"path {args.media_dir} doesn't exist, maybe not mounted?"
  setup_logger(log_filename=f"./logs/matches_{short_fname(args.media_dir)}.log")
  App(args.media_dir, args.mode).run(args.num_participants)

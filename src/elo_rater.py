import os
import sys
import logging

from helpers import short_fname
from elo_rater_types import Outcome
from elo_rater_view import EloGui
from elo_rater_model import EloCompetition


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

class App:
  def __init__(self, media_dir:str):
    self.gui = EloGui()
    self.model = EloCompetition(media_dir, refresh=False)

  def consume_result(self, outcome:Outcome) -> None:
    participants = self.model.get_curr_match() #needs to be before model.consume_result()
    elo_changes = self.model.consume_result(outcome)
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants, outcome)
    self.gui.conclude_match(elo_changes, self.start_next_match)

  def start_next_match(self) -> None:
    participants = self.model.generate_match()
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants)
    self.gui.display_match(participants, self.consume_result)

  def run(self) -> None:
    self.start_next_match()
    self.gui.mainloop()


if __name__ == "__main__":
  given_dir = sys.argv[1] if len(sys.argv)>1 else "./test_imgs/"
  given_dir = os.path.abspath(given_dir)
  assert os.path.exists(given_dir), f"path {given_dir} doesn't exist"

  setup_logger(log_filename=f"./logs/matches_{short_fname(given_dir)}.log")
  App(given_dir).run()

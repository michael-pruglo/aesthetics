import os
import sys
import logging

from helpers import short_fname
from ae_rater_types import Outcome
from ae_rater_view import RaterGui
from ae_rater_model import RatingCompetition


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
    self.model = RatingCompetition(media_dir, refresh=False)
    self.gui = RaterGui(give_boost_cb=self._give_boost)

  def run(self, num_participants:int) -> None:
    try:
      self._start_next_match(num_participants)
      self.gui.mainloop()
    except Exception:
      logging.exception("")
    finally:
      self.model.on_exit()

  def _consume_result(self, outcome:Outcome) -> None:
    participants = self.model.get_curr_match() #needs to be before model.consume_result()
    rating_opinions = self.model.consume_result(outcome)
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants, outcome)
    self.gui.conclude_match(rating_opinions, self._start_next_match)

  def _start_next_match(self, num_participants:int) -> None:
    participants = self.model.generate_match(num_participants)
    self.gui.display_leaderboard(self.model.get_leaderboard(), participants)
    self.gui.display_match(participants, self._consume_result)

  def _give_boost(self, short_name:str) -> None:
    self.model.give_boost(short_name)
    updated_prof = self.model.get_curr_match()
    self.gui.display_leaderboard(self.model.get_leaderboard(), updated_prof)
    self.gui.display_match(updated_prof, self._consume_result)


if __name__ == "__main__":
  given_dir = sys.argv[1] if len(sys.argv)>1 else "./sample_imgs/"
  given_dir = os.path.abspath(given_dir)
  assert os.path.exists(given_dir), f"path {given_dir} doesn't exist"

  num_participants = int(sys.argv[2]) if len(sys.argv)>2 else 2

  setup_logger(log_filename=f"./logs/matches_{short_fname(given_dir)}.log")
  App(given_dir).run(num_participants)

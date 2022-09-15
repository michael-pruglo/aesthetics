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

def run_rater(media_dir):
  gui = EloGui()
  model = EloCompetition(media_dir, refresh=False)

  def consume_result(outcome:Outcome):
    elo_change = model.consume_result(outcome)
    gui.conclude_match(elo_change, start_next_match)

  def start_next_match():
    gui.display_match(model.get_next_match(), consume_result)

  start_next_match()
  gui.mainloop()


if __name__ == "__main__":
  given_dir = sys.argv[1] if len(sys.argv)>1 else "./test_imgs/"
  given_dir = os.path.abspath(given_dir)
  assert os.path.exists(given_dir), f"path {given_dir} doesn't exist"

  setup_logger(log_filename=f"./logs/matches_{short_fname(given_dir)}.log")
  run_rater(given_dir)

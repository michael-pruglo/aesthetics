import os, sys
import logging

from elo_rater_types import Outcome
from elo_rater_view import EloGui
from elo_rater_model import EloCompetition


def setup_logger(media_dir):
  log_filename = f"matches_{media_dir.split('/')[-1]}.log"
  print(f"logging to file {log_filename}")

  logging.basicConfig(
    handlers = [
      logging.StreamHandler(),
      logging.FileHandler(log_filename, encoding="utf-8")
    ],
    format = "%(asctime)s %(message)s",
    datefmt = "%Y-%m-%d %H:%M",
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
    gui.display_match(*model.get_next_match(), consume_result)

  start_next_match()
  gui.mainloop()


if __name__ == "__main__":
  media_dir = sys.argv[1] if len(sys.argv)>1 else "./test_imgs/"
  media_dir = os.path.abspath(media_dir)
  assert os.path.exists(media_dir), f"path {media_dir} doesn't exist"

  setup_logger(media_dir)
  run_rater(media_dir)

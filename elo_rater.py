from elo_rater_types import Outcome
from elo_rater_view import EloGui
from elo_rater_model import EloCompetition

import os


def main():
  gui = EloGui()
  model = EloCompetition(os.path.abspath('./test_imgs/'), refresh=False)

  def consume_result(outcome:Outcome):
    elo_change = model.consume_result(outcome)
    gui.conclude_match(elo_change, start_next_match)

  def start_next_match():
    gui.display_match(*model.get_next_match(), consume_result)

  start_next_match()
  gui.mainloop()


if __name__ == "__main__":
  main()

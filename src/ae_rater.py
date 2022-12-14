#!/usr/bin/env python3

import os
import logging
import argparse

from helpers import short_fname
from ae_rater_types import AppMode, ManualMetadata, Outcome, UserListener, MatchInfo
from ae_rater_view import RaterGui
from ae_rater_model import Analyzer, DBAccess, RatingCompetition
from ai_assistant import Assistant
from prioritizers import PrioritizerType


def setup_logger(log_filename):
  print(f"logging to file {log_filename}")
  logging.basicConfig(
    handlers = [
      logging.StreamHandler(),
      logging.FileHandler(log_filename, encoding="utf-8")
    ],
    # format = "%(created)d %(message)s",
    format = "[%(filename)20s:%(lineno)4s - %(funcName)20s() ] %(message)s",
    level = logging.INFO
  )
  logging.info("Starting new session...")


class Controller:
  def __init__(self, media_dir:str, refresh:bool) -> None:
    self.competition = RatingCompetition()
    self.db = DBAccess(media_dir, refresh)
    self.db.set_sysnames(self.competition.get_sysnames())
    self.analyzer = Analyzer()

  def process_match(self, match:MatchInfo):
    logging.info("exec %s", str(match))
    opinions,diagnostic_info = self.competition.consume_match(match)
    self.analyzer.consume_diagnostic(diagnostic_info)
    self.db.apply_opinions(match.profiles, opinions)

class FromHistoryController(Controller):
  def __init__(self, media_dir:str):
    super().__init__(media_dir, False)

  def run(self):
    logging.info("exec")
    for match in self.db.get_match_history():
      self.process_match(match)

class InteractiveController(Controller, UserListener):
  def __init__(self, media_dir:str, refresh:bool, n_participants:int, prioritizer_type, mode:AppMode) -> None:
    super().__init__(media_dir, refresh)
    self.n = n_participants
    self.db.set_prioritizer(prioritizer_type)
    self.mode = mode
    self.gui = RaterGui(self, self.db.get_tags_vocab(), mode)
    self.participants = []
    self.ai_assistant = Assistant()

  def run(self) -> None:
    logging.info("exec")
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
      self.db.on_exit()

  def start_next_match(self):
    logging.info("exec")
    self.participants = self.db.get_next_match(self.n)
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.display_match(self.participants)

  def consume_result(self, outcome:Outcome) -> None:
    logging.info("exec")
    assert self.n and len(self.participants) == self.n
    match = MatchInfo(profiles=self.participants, outcome=outcome)
    self.process_match(match)
    self.db.save_match(match)
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.conclude_match()
    self.participants = []

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    logging.info("exec")
    self.db.update_meta(fullname, meta)
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.refresh_profile(self.db.get_profile(fullname))

  def suggest_tags(self, fullname:str) -> list:
    logging.info("exec")
    return self.ai_assistant.suggest_tags(fullname)

  def search_for(self, query:str) -> None:
    logging.info("exec")
    N = 8
    res = self.db.get_search_results(query)[:N]
    self.gui.display_leaderboard(self.db.get_leaderboard(), res)
    self.gui.display_match(res, N)


def main(args):
  assert os.path.exists(args.media_dir), f"path {args.media_dir} doesn't exist, maybe not mounted?"
  setup_logger(log_filename=f"./logs/matches_{short_fname(args.media_dir)}.log")
  interactive = True
  if interactive:
    InteractiveController(
      args.media_dir,
      args.refresh,
      args.num_participants,
      args.prioritizer_type,
      args.mode
    ).run()


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('-r', '--refresh', dest='refresh', action='store_const',
                      const=True, default=False,
                      help="refresh db to incorporate folder updates")
  parser.add_argument('-p', '--prioritizer', dest='prioritizer_type', type=PrioritizerType,
                      choices=list(PrioritizerType), default=PrioritizerType.DEFAULT,
                      help="which media is prioritized for matches")
  parser.add_argument('-s', '--search', dest='mode', action='store_const',
                      const=AppMode.SEARCH, default=AppMode.MATCH,
                      help="run SEARCH instead of MATCH mode")
  parser.add_argument('media_dir', nargs='?', default="./sample_imgs/",
                      help="media folder to operate on")
  parser.add_argument('num_participants', type=int, nargs='?', default=2,
                      help="number of participants in MATCH mode")

  main(parser.parse_args())

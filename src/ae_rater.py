#!/usr/bin/env python3

import os
import logging
import argparse
from tqdm import tqdm

from helpers import short_fname
from ae_rater_types import AppMode, Outcome, UserListener, MatchInfo
from metadata import ManualMetadata
from ae_rater_view import MatchGui, SearchGui
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
    format = "%(created)d %(message)s",
    level = logging.INFO
  )
  logging.info("Starting new session...")


INITIAL_METADATA_FNAME = "backup_initial_metadata.csv"
DEFAULT_HISTORY_FNAME = "match_history.csv"

class Controller:
  def __init__(self, media_dir:str, refresh:bool, prioritizer_type=PrioritizerType.DEFAULT, history_fname=DEFAULT_HISTORY_FNAME) -> None:
    self.competition = RatingCompetition()
    self.db = DBAccess(media_dir, refresh, prioritizer_type, self.competition.get_rat_systems(), history_fname)
    self.analyzer = Analyzer()

  def process_match(self, match:MatchInfo):
    opinions,diagnostic_info = self.competition.consume_match(match)
    self.analyzer.consume_diagnostic(diagnostic_info)
    self.db.apply_opinions(match.profiles, opinions)

class FromHistoryController(Controller):
  def __init__(self, media_dir:str, history_fname:str=DEFAULT_HISTORY_FNAME):
    super().__init__(media_dir, refresh=False, history_fname=history_fname)

  def run(self, with_diagnostics=True):
    logging.info("preparing to re-run history: resetting meta to initial...")
    self.db.reset_meta_to_initial()
    for match in tqdm(self.db.get_match_history()):
      self.process_match(match)
    if with_diagnostics:
      self.analyzer.show_results()

class InteractiveController(Controller, UserListener):
  def __init__(self, media_dir:str, refresh:bool, n_participants:int, prioritizer_type, mode:AppMode) -> None:
    super().__init__(media_dir, refresh, prioritizer_type)
    self.n = n_participants
    self.mode = mode
    self.gui = MatchGui(self) if mode==AppMode.MATCH else SearchGui(self)
    self.participants = []
    self.ai_assistant = Assistant()

  def run(self) -> None:
    try:
      if self.mode == AppMode.MATCH:
        self.start_next_match()
      elif self.mode == AppMode.SEARCH:
        self.search_for("", page=1)
      else:
        raise RuntimeError(f"cannot run mode {self.mode}")
      self.gui.mainloop()
    except Exception:
      logging.exception("")
    finally:
      self.db.on_exit()

  def start_next_match(self):
    self.participants = self.db.get_next_match(self.n)
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.display_match(self.participants)

  def consume_result(self, outcome:Outcome) -> None:
    assert self.n and len(self.participants) == self.n
    assert self.n == len(outcome.tiers) - outcome.tiers.count(' ')
    match = MatchInfo(profiles=self.participants, outcome=outcome)
    self.process_match(match)
    self.db.save_match(match)
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.conclude_match()
    self.participants = []

  def update_meta(self, fullname:str, meta:ManualMetadata) -> None:
    self.db.update_meta(fullname, meta)
    updated_prof = self.db.get_profile(fullname)
    self.participants = [updated_prof if p.fullname==fullname else p for p in self.participants]
    self.gui.display_leaderboard(self.db.get_leaderboard(), self.participants)
    self.gui.refresh_profile(updated_prof)

  def suggest_tags(self, fullname:str) -> list:
    return self.ai_assistant.suggest_tags(fullname)

  def search_for(self, query:str, page:int=1) -> None:
    res = self.db.get_search_results(query)[self.n*(page-1) : self.n*page]
    self.gui.display_leaderboard(self.db.get_leaderboard(), res)
    self.gui.display_match(res, self.n)


def main(args):
  assert os.path.exists(args.media_dir), f"path {args.media_dir} doesn't exist, maybe not mounted?"
  setup_logger(log_filename=f"./logs/matches_{short_fname(args.media_dir)}.log")
  if args.history_replay:
    FromHistoryController(
      args.media_dir,
    ).run()
  else:
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
  parser.add_argument('--history_replay', dest='history_replay', action='store_const',
                      const=True, default=False,
                      help="replay matches from history instead of interactive matches")
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

import time
import unittest
import os
import pandas as pd
import random
import string
from ae_rater import Controller, FromHistoryController

from ae_rater_types import MatchInfo, Outcome, ProfileInfo
from ae_rater_model import RatingCompetition
from helpers import short_fname
from metadata import get_metadata, write_metadata
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER


def rndstr(length:int=11) -> str:
  return ''.join(random.sample(string.ascii_letters+" ", length))


class TestCompetition(unittest.TestCase):
  def setUp(self) -> None:
    self.model = RatingCompetition()
    self.sysnames = [s.name() for s in self.model.get_rat_systems()]

  def _generate_match(self, stars:list[float], outcome_str:str) -> MatchInfo:
    return MatchInfo(
      profiles=[ProfileInfo(
        fullname=rndstr(),
        tags=rndstr(),
        stars=strs,
        ratings={sys.name():sys.stars_to_rating(strs) for sys in self.model.get_rat_systems()},
        nmatches=random.randint(0,100),
        awards=rndstr(),
      ) for strs in stars],
      outcome=Outcome(outcome_str),
    )

  def _test_match(self, participants_stars:list[float], outcome_str:str):
    match = self._generate_match(participants_stars, outcome_str)
    rat_opinions, diagnostic = self.model.consume_match(match)
    for sname, li in rat_opinions.items():
      self.assertTrue(sname in self.sysnames)
      self.assertEqual(len(li), len(match.profiles))
      win_idx = Outcome.let_to_idx(outcome_str[0])
      los_idx = Outcome.let_to_idx(outcome_str[-1])
      self.assertGreater(li[win_idx].new_rating, match.profiles[win_idx].ratings[sname])
      self.assertGreater(li[win_idx].delta_rating, 0)
      self.assertGreater(li[win_idx].new_stars, match.profiles[win_idx].stars)
      self.assertLess(li[los_idx].new_rating, match.profiles[los_idx].ratings[sname])
      self.assertLess(li[los_idx].delta_rating, 0)
      self.assertLess(li[los_idx].new_stars, match.profiles[los_idx].stars)
    self.assertEqual(diagnostic, "diagnostic")

  def test_underdog_wins(self):
    self._test_match([1.3, 4.4], "a b")
    self._test_match([3.9, 0.1], "b a")

  def test_mixed(self):
    self._test_match([3.4, 2.4, 1.7, 4.0, 1.3, 2.4, 0.8], "c f--a bd+e g")
    self._test_match([1.1, 2.9, 0.1, 5.0, 4.9, 3.3], "a b c+ d e+ f")
    self._test_match([2.7, 5.1, 0.9, 2.1, 2.2, 1.4, 1.1], "g++ ab d e f c")
    self._test_match([3.4, 3.3, 1.1, 2.0, 4.1], "d ae- c b")
    self._test_match([1.1, 4.1, 2.2], "c+ b++ a")


class TestLongTerm(unittest.TestCase):
  def setUp(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

  def tearDown(self):
    hlp.disk_cleanup()

  def _long_term(self, ctrl:Controller, n:int):
    losses = LongTermTester(ctrl, n, verbosity=1).run()
    self.assertLess(losses[-1], 0.9, f"num_participants={n}")
    self.assertLess(losses[-1]/losses[0], 10)

  def test_regular_2(self):
    self._long_term(Controller(MEDIA_FOLDER, refresh=False), 2)

  def test_regular_3plus(self):
    self._long_term(Controller(MEDIA_FOLDER, refresh=False), random.randint(3,12))

  def test_history_short(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    assert len(all_files) > 9, "need more samples for this test"
    test_files = random.sample(all_files, 10)
    for i,fullname in enumerate(test_files):
      meta = get_metadata(fullname)
      meta.stars = 5 - 5*i//len(test_files)
      write_metadata(fullname, meta, append=False)

    HIST_FNAME = 'test_history_short.csv'
    def p_names(ranks:list[int]):
      return str([short_fname(test_files[i]) for i in ranks])

    now = time.time()
    df = pd.DataFrame(
      [
        [now+1.0, p_names([-2,1,0,-1]), "bc ad"],
        [now+1.1, p_names([0,-1]), "b a"],
        [now+1.2, p_names([4,5]), "ab"],
        [now+1.3, p_names([-2,-3,1]), "c b a"],
        [now+1.4, p_names([3,4]), "a b"],
      ],
      columns=["timestamp","names","outcome"],
    )
    df.to_csv(os.path.join(MEDIA_FOLDER, HIST_FNAME), index=False)

    ctrl = FromHistoryController(MEDIA_FOLDER, HIST_FNAME)
    ldbrd_pre = filter(lambda p: p.fullname in test_files, ctrl.db.get_leaderboard())
    for p in ldbrd_pre:
      self.assertEqual(p.nmatches, 0)

    ctrl.run()

    ldbrd_post = list(filter(lambda p: p.fullname in test_files, ctrl.db.get_leaderboard()))

    expected_rankings = [1,0,3,2,5,4,7,6,9,8]
    expected_nmatches = [5,4,1,0,1,2,2,0,4,5]
    self.assertListEqual(
      [p.fullname for p in ldbrd_post],
      [test_files[i] for i in expected_rankings]
    )
    self.assertListEqual(
      [p.nmatches for p in ldbrd_post],
      expected_nmatches
    )


  def test_history_repeats(self):
    pass


class LongTermTester:
  def __init__(self, ctrl:Controller, num_participants:int, verbosity=0):
    self.ctrl = ctrl
    self.num_participants = num_participants
    self.verbosity = verbosity
    ldbrd = ctrl.db.get_leaderboard()
    ranks = list(range(len(ldbrd)))
    random.shuffle(ranks)
    self.true_leaderboard = {p.fullname:rank for p,rank in zip(ldbrd,ranks)}

  def run(self, epochs=15, matches_each=20) -> list[float]:
    if self.verbosity: print()
    losses = []
    for epoch in range(epochs):
      matches_in_epoch = matches_each*len(self.true_leaderboard)
      matches_in_iter = (self.num_participants-1) * self.num_participants
      num_of_iters = (matches_in_epoch+matches_in_iter-1)//matches_in_iter
      for _ in range(num_of_iters):
        participants = self.ctrl.db.get_next_match(self.num_participants)
        minfo = MatchInfo(participants, self._simulate_outcome(participants))
        self.ctrl.process_match(minfo)
      losses.append(self._loss())
      if self.verbosity: print(f"{epoch}: loss = {losses[-1]}")
      if self.verbosity>1: print("\n\n\n")
      if losses[-1] < 0.1:
        return losses

    return losses

  def _simulate_outcome(self, participants:list[ProfileInfo]) -> Outcome:
    li = [(self.true_leaderboard[p.fullname], Outcome.idx_to_let(i)) for i,p in enumerate(participants)]
    li.sort(key=lambda tup:tup[0])
    tiers = li[0][1]
    for i in range(1,len(li)):
      prev_rank, curr_rank = li[i-1][0], li[i][0]
      tiers += " "*(prev_rank < curr_rank-2)
      tiers += li[i][1]
    assert Outcome.is_valid(tiers, len(participants))
    return Outcome(tiers)

  def _loss(self) -> float:
    sq_err = 0
    ldbrd = self.ctrl.db.get_leaderboard()
    for given_rating, p in enumerate(ldbrd):
      expected_rating = self.true_leaderboard[p.fullname]
      if self.verbosity>1: print(p, expected_rating)
      sq_err += (expected_rating-given_rating)**2 * (p.stars/5)
    assert hlp.is_sorted(ldbrd)
    return sq_err / len(ldbrd)


if __name__ == '__main__':
  unittest.main()

import unittest
import os
import random
import string

from metadata import get_metadata
from ae_rater_types import MatchInfo, Outcome, ProfileInfo
from ae_rater_model import RatingCompetition
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER, SKIPLONG, generate_outcome


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


@unittest.skip('old')
class TestCompetitionOld(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)
    self.N = len(self.model.get_leaderboard())

  def test_matches_affect_disk(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    for _ in range(20):
      n = random.randint(2, min(15,len(all_files)))
      participants = self.model.generate_match(n)
      metadata = [get_metadata(p.fullname) for p in participants]
      outcome = generate_outcome(n)
      self.model.consume_result(outcome)
      self.assertEqual(len(self.model.get_curr_match()), 0)
      news = [self._get_leaderboard_line(p.fullname) for p in participants]
      new_metadata = [get_metadata(p.fullname) for p in participants]

      for old_p, old_meta, new_p, new_meta in zip(participants, metadata, news, new_metadata):
        dbg_info = '\n'.join(map(str, [old_p, old_meta, new_p, new_meta]))
        self.assertEqual(new_p.nmatches, old_p.nmatches+len(participants)-1, dbg_info)
        self.assertSetEqual(old_meta.tags, new_meta.tags)
        self.assertEqual(old_meta.awards, new_meta.awards)
        self.assertEqual(min(5, int(old_p.stars)), old_meta.stars)
        self.assertEqual(min(5, int(new_p.stars)), new_meta.stars)
        for ratsys in old_p.ratings.keys():
          old_rating = old_p.ratings[ratsys]
          new_rating = new_p.ratings[ratsys]
          self.assertLessEqual(new_rating.rd, old_rating.rd)
          self.assertGreaterEqual(new_rating.timestamp, old_rating.timestamp)



  def _long_term(self, n):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    losses = LongTermTester(self.model, num_participants=n, verbosity=1).run()
    self.assertLess(losses[-1], 0.9, f"num_participants={n}")
    self.assertLess(losses[-1]/losses[0], 10)

  @unittest.skipIf(*SKIPLONG)
  def test_long_term_2(self):
    self._long_term(2)

  @unittest.skipIf(*SKIPLONG)
  def test_long_term_3plus(self):
    hi = min(12, self.N-3)
    if hi<3:
      self.fail(f"{self.N} images is not enough")
    else:
      self._long_term(random.randint(3, hi))


class LongTermTester:
  def __init__(self, model:RatingCompetition, num_participants:int, verbosity=0):
    self.model = model
    self.num_participants = num_participants
    self.verbosity = verbosity
    ldbrd = model.get_leaderboard()
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
        participants = self.model.generate_match(self.num_participants)
        self.model.consume_result(self._simulate_outcome(participants))
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
    ldbrd = self.model.get_leaderboard()
    for given_rating, p in enumerate(ldbrd):
      expected_rating = self.true_leaderboard[p.fullname]
      if self.verbosity>1: print(p, expected_rating)
      sq_err += (expected_rating-given_rating)**2
    assert is_sorted(ldbrd)
    return sq_err / len(ldbrd)


if __name__ == '__main__':
  unittest.main()

import statistics
import unittest
import os
import random

from src.helpers import short_fname
from metadata import get_metadata
from ae_rater_types import Outcome, ProfileInfo
from ae_rater_model import RatingCompetition
import tests.helpers as hlp
from tests.helpers import MEDIA_FOLDER, SKIPLONG, generate_outcome


def is_sorted(l:list[ProfileInfo]) -> bool:
  for i, curr_prof in enumerate(l[:-1]):
    next_prof = l[i+1]
    if curr_prof.stars < next_prof.stars:
      return False
    if all(curr_prof.ratings[s].points < next_prof.ratings[s].points
           for s in curr_prof.ratings.keys()):
      return False
  return True


class TestCompetition(unittest.TestCase):
  def setUp(self):
    self.model = RatingCompetition(MEDIA_FOLDER, refresh=False)
    self.N = len(self.model.get_leaderboard())

  def tearDown(self):
    hlp.disk_cleanup()

  def _get_leaderboard_line(self, fullname:str) -> ProfileInfo:
    ldbrd = self.model.get_leaderboard()
    return next(p for p in ldbrd if p.fullname==fullname)

  def test_match_generation(self):
    def all_unique(li):
      seen = list()
      return not any(i in seen or seen.append(i) for i in li)

    for _ in range(15):
      participants = self.model.generate_match()
      self.assertTrue(all_unique(participants))
      self.assertListEqual(self.model.get_curr_match(), participants)

  def test_get_leaderboard(self):
    ldbrd = self.model.get_leaderboard()
    mediafiles = hlp.get_initial_mediafiles()
    self.assertTrue(is_sorted(ldbrd))
    self.assertSetEqual({short_fname(p.fullname) for p in ldbrd}, set(mediafiles))

  def test_boost_generic(self):
    p = self.model.generate_match()[0]
    profile_before = self._get_leaderboard_line(p.fullname)
    self.assertEqual(p, profile_before)
    hlp.backup_files([p.fullname])
    self.model.give_boost(short_fname(p.fullname))
    profile_after = self._get_leaderboard_line(p.fullname)
    self.assertEqual(profile_after.tags, profile_after.tags)
    self.assertEqual(profile_before.nmatches, profile_after.nmatches)
    self.assertLessEqual(profile_before.stars, profile_after.stars)
    self.assertTrue(all(profile_before.ratings[s].points < profile_after.ratings[s].points
                        for s in profile_before.ratings.keys()))

  def test_boost_starchange(self):
    hlp.backup_files([os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()])
    for times in range(3):
      prof = self.model.generate_match()[0]
      stars_before = prof.stars
      for iter in range(25):
        self.model.give_boost(short_fname(prof.fullname))
        curr_stars_opinions = [s.get_boost(prof).new_stars for s in self.model.rat_systems]
        consensus_stars = statistics.mean(curr_stars_opinions)
        self.assertGreater(consensus_stars, stars_before)
        profile_after = self._get_leaderboard_line(prof.fullname)
        dbg_info = f"curr profile: {prof},  profile_aftter: {profile_after}, opinions:{curr_stars_opinions}"
        self.assertEqual(profile_after.stars, consensus_stars, dbg_info)
        if int(consensus_stars) != int(stars_before):
          self.assertEqual(int(consensus_stars), int(stars_before)+1, dbg_info)
          _, disk_stars = get_metadata(prof.fullname)
          self.assertEqual(disk_stars, int(consensus_stars), dbg_info)
          break
        prof = profile_after

  def test_matches_affect_disk(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    for _ in range(42):
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
        disk_tags_old, disk_tags_new = old_meta[0], new_meta[0]
        disk_stars_old, disk_stars_new = old_meta[1], new_meta[1]
        self.assertSetEqual(disk_tags_old, disk_tags_new)
        self.assertEqual(int(old_p.stars), disk_stars_old)
        self.assertEqual(int(new_p.stars), disk_stars_new)
        for ratsys in old_p.ratings.keys():
          old_rating = old_p.ratings[ratsys]
          new_rating = new_p.ratings[ratsys]
          self.assertLessEqual(new_rating.rd, old_rating.rd)
          self.assertGreaterEqual(new_rating.timestamp, old_rating.timestamp)

  def _long_term(self, n):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    hlp.backup_files(all_files)

    losses = LongTermTester(self.model, num_participants=n, verbosity=1).run()
    self.assertLess(losses[-1], 0.9)
    self.assertLess(losses[-1]/losses[0], 10)

  @unittest.skipIf(*SKIPLONG)
  def test_long_term_2(self):
    self._long_term(2)

  @unittest.skipIf(*SKIPLONG)
  def test_long_term_3plus(self):
    self._long_term(random.randint(3, max(3,self.N-3)))


class LongTermTester:
  def __init__(self, model:RatingCompetition, num_participants:int, verbosity=0):
    self.model = model
    self.num_participants = num_participants
    self.verbosity = verbosity
    ldbrd = model.get_leaderboard()
    ranks = list(range(len(ldbrd)))
    random.shuffle(ranks)
    self.true_leaderboard = {p.fullname:rank for p,rank in zip(ldbrd,ranks)}

  def run(self, epochs=10, matches_each=20) -> list[float]:
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
      if losses[-1] == 0:
        return losses

    return losses

  def _simulate_outcome(self, participants:list[ProfileInfo]) -> Outcome:
    li = [(self.true_leaderboard[p.fullname], chr(ord('a')+i)) for i,p in enumerate(participants)]
    li.sort(key=lambda tup:tup[0])
    tiers = li[0][1]
    for i in range(1,len(li)):
      prev_rank, curr_rank = li[i-1][0], li[i][0]
      tiers += " "*(prev_rank < curr_rank-2)
      tiers += li[i][1]
    outcome = Outcome(tiers)
    assert outcome.is_valid(len(participants))
    return outcome

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

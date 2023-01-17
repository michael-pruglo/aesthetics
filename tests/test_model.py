import copy
import operator
import statistics
from string import ascii_letters
import unittest
import os
import random
import string
from math import sqrt

from src.helpers import short_fname
from metadata import get_metadata
from ae_rater_types import ManualMetadata, MatchInfo, Outcome, ProfileInfo
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

def factorize(n:int) -> list[int]:
  for i in range(2, int(sqrt(n)+1)):
    if n%i == 0:
      return [i] + factorize(n//i)
  return [n]

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

  def test_underdog_wins(self):
    match = self._generate_match([1.3, 4.4], "a b")
    rat_opinions, diagnostic = self.model.consume_match(match)
    for sname, li in rat_opinions.items():
      self.assertTrue(sname in self.sysnames)
      self.assertEqual(len(li), len(match.profiles))
      self.assertGreater(li[0].new_rating, match.profiles[0].ratings[sname])
      self.assertGreater(li[0].delta_rating, 0)
      self.assertGreater(li[0].new_stars, match.profiles[0].stars)
      self.assertLess(li[1].new_rating, match.profiles[1].ratings[sname])
      self.assertLess(li[1].delta_rating, 0)
      self.assertLess(li[1].new_stars, match.profiles[1].stars)
    self.assertEqual(diagnostic, "diagnostic")


@unittest.skip('old')
class TestCompetitionOld(unittest.TestCase):
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
    mult = 0
    while mult ==0: mult = random.randint(-7, 7)
    self.model.give_boost(short_fname(p.fullname), mult)
    profile_after = self._get_leaderboard_line(p.fullname)
    self.assertEqual(profile_after.tags, profile_after.tags)
    self.assertEqual(profile_before.nmatches, profile_after.nmatches)
    if mult > 0:
      self.assertLessEqual(profile_before.stars, profile_after.stars)
      ratop = operator.lt
    else:
      self.assertGreaterEqual(profile_before.stars, profile_after.stars)
      ratop = operator.gt

    self.assertTrue(all(ratop(profile_before.ratings[s].points,
                              profile_after.ratings[s].points)
                        for s in profile_before.ratings.keys()))

  def test_boost_starchange(self):
    hlp.backup_files([os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()])
    for times in range(3):
      prof = self.model.generate_match()[0]
      stars_before = prof.stars
      for iter in range(25):
        self.model.give_boost(short_fname(prof.fullname), 1)
        curr_stars_opinions = [s.get_boost(prof, 1).new_stars for s in self.model.rat_systems]
        consensus_stars = statistics.mean(curr_stars_opinions)
        self.assertGreater(consensus_stars, stars_before)
        profile_after = self._get_leaderboard_line(prof.fullname)
        dbg_info = f"curr profile: {prof},  profile_aftter: {profile_after}, opinions:{curr_stars_opinions}"
        self.assertEqual(profile_after.stars, consensus_stars, dbg_info)
        if consensus_stars<=5 and int(consensus_stars)!=int(stars_before):
          self.assertEqual(int(consensus_stars), int(stars_before)+1, dbg_info)
          disk_meta = get_metadata(prof.fullname)
          self.assertEqual(disk_meta.stars, int(consensus_stars), dbg_info)
          break
        prof = profile_after

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

  def _test_meta_update_impl(self, usr_input:ManualMetadata):
    N = 8
    testees = self.model.generate_match(N)
    hlp.backup_files([p.fullname for p in testees])
    self.model.consume_result(Outcome(' '.join(ascii_letters[:N])))  # to achieve fractional stars
    testees = [self._get_leaderboard_line(p.fullname) for p in testees]

    same_stars = [True]*(N//2) + [False]*(N-N//2)  # if curr stars are 2.4, input 2 shouldn't change it
    for prof, frac_int_test in zip(testees, same_stars):
      meta_before = get_metadata(prof.fullname)
      self.assertEqual(meta_before.stars, int(prof.stars))
      self.assertSetEqual(meta_before.tags, set(prof.tags.split()))
      if meta_before.awards:
        self.assertSetEqual(meta_before.awards, set(prof.awards.split()), prof.fullname)
      if frac_int_test and usr_input.stars is not None:
        usr_input.stars = meta_before.stars

      self.model.update_meta(prof.fullname, copy.deepcopy(usr_input))  # input is allowed to be modified
      exp_stars = meta_before.stars if usr_input.stars is None else usr_input.stars
      exp_tags = meta_before.tags if usr_input.tags is None else set(usr_input.tags)
      exp_awards = meta_before.awards if usr_input.awards is None else set(usr_input.awards)

      dbg_info = f"{short_fname(prof.fullname)} frac_int:{frac_int_test}"
      meta_after = get_metadata(prof.fullname)
      self.assertEqual(meta_after.stars, exp_stars)
      if usr_input.tags is not None:
        self.assertNotEqual(meta_after.tags, meta_before.tags, dbg_info)
      self.assertSetEqual(meta_after.tags, exp_tags, dbg_info)
      if meta_after.awards:
        self.assertSetEqual(meta_after.awards, exp_awards, dbg_info)
      new_prof = self._get_leaderboard_line(prof.fullname)
      self.assertEqual(min(5,int(new_prof.stars)), exp_stars, dbg_info)
      self.assertSetEqual(set(new_prof.tags.split()), exp_tags, dbg_info)
      if new_prof.awards:
        self.assertSetEqual(set(new_prof.awards.split()), exp_awards, dbg_info)

  def test_meta_update_0(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        stars = random.randint(0, 5),
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_1(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = None,
        stars = random.randint(0, 5),
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_2(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        stars = None,
        awards = {"awa1", "awa2", "awa3"},
    ))

  def test_meta_update_3(self):
    self._test_meta_update_impl(ManualMetadata(
        tags = {"nonsense", "sks", "u3jm69ak2m6jo"},
        stars = random.randint(0, 5),
        awards = None,
    ))

  def test_search_results(self):
    all_files = [os.path.join(MEDIA_FOLDER, f) for f in hlp.get_initial_mediafiles()]
    assert len(all_files) > 9, "need more samples for this test"
    test_files = random.sample(all_files, 10)
    hlp.backup_files(test_files)
    for i,fullname in enumerate(test_files):
      searchable_meta = ManualMetadata(
        tags=[f"tag{i}", f"factors{'#'.join(map(str, factorize(i)))}"],
        stars=5-5*i//len(test_files),
        awards=[f"awa{i}"],
      )
      self.model.update_meta(fullname, searchable_meta)

    def assert_searches(query, idxs, context=""):
      self.assertListEqual(
        self.model.get_search_results(query),
        [
          self._get_leaderboard_line(test_files[i])
          for i in idxs
        ],
        context,
      )
    assert_searches("tag9 awa9", [9], "AND, with results")
    assert_searches("tag9 awa8", [], "AND, empty")
    assert_searches("tag9|awa6", [6,9], "OR")
    self.assertEqual(len(self.model.get_search_results("-tag9")), len(all_files)-1)
    self.assertSetEqual(
      {p.fullname for p in self.model.get_search_results("mp4")},
      {fname for fname in all_files if fname.lower().endswith(".mp4")},
      "search filenames"
    )
    assert_searches("factors2", [2,4,6,8])
    assert_searches("2#2", [4,8])
    assert_searches("#3", [6,9])
    assert_searches("2# -#3 -3#", [4,8], "AND NOT")
    assert_searches("3#|#3", [6,9], "OR")
    assert_searches("factors7 | 2#2 -2#2#", [4,7], "complex")

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

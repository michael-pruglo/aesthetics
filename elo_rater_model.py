from elo_rater_types import EloChange, ProfileInfo
from metadata import MetadataManager

import os
from numpy import int64
from typing import Tuple


class EloCompetition:
    def __init__(self, img_dir, refresh):
        self.img_dir = img_dir
        self.meta_mgr = MetadataManager(img_dir, refresh)

    def get_next_match(self) -> Tuple[ProfileInfo, ProfileInfo]:
        return self._retreive_profile("dog.jpg"), self._retreive_profile("cat.mp4")

    def consume_result(self, right_wins:bool) -> EloChange:
        return EloChange(1337, +250, 987, -250)

    def _retreive_profile(self, short_name) -> ProfileInfo:
        try:
            info = self.meta_mgr.get_file_info(short_name)
        except KeyError as e:
            print(e)
            return ProfileInfo("-", "err", -1, -1, -1)

        assert all(info.index == ['tags', 'rating', 'elo', 'elo_matches'])
        assert type(info['tags']) == str
        assert type(info['rating']) == int64
        assert type(info['elo']) == int64
        assert type(info['elo_matches']) == int64
        return ProfileInfo(
            tags = info['tags'],
            fullname = os.path.join(self.img_dir, short_name),
            rating = info['rating'],
            elo = info['elo'],
            elo_matches = info['elo_matches'],
        )

from dataclasses import dataclass

@dataclass
class ProfileInfo:
    tags : str
    fullname : str
    rating : int
    elo : int
    elo_matches : int

    def short_name(self):
        return self.fullname.split('/')[-1]

@dataclass
class EloChange:
    new_elo_1 : int
    new_elo_2 : int
    delta_elo_1 : int
    delta_elo_2 : int

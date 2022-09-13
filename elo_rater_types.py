from dataclasses import dataclass
from helpers import truncate


def elo_class(elo:int) -> int:
    """divide into 6 classes (0-5 stars) based on elo"""
    if   elo >= 2000: return 5
    elif elo >= 1800: return 4
    elif elo >= 1600: return 3
    elif elo >= 1400: return 2
    elif elo >= 1200: return 1
    else:             return 0


@dataclass
class ProfileInfo:
    tags : str
    fullname : str
    rating : int
    elo : int
    elo_matches : int

    def short_name(self):
        return self.fullname.split('/')[-1]
    
    def __str__(self):
        BG_GRAY     = "\033[48;5;236m"
        FG_WHITE    = "\033[38;5;231m"
        FG_YELLOW   = "\033[38;5;214m"
        FG_ELO      = "\033[38;5;{}m".format([0,26,2,228,208,9][elo_class(self.elo)])
        COLOR_RESET = "\033[0;0m"
        return ''.join([
            BG_GRAY,
            FG_WHITE,   f"{truncate(self.short_name(), 15):<15} ",
            FG_YELLOW,  f"{'★' * self.rating:>5} ",
            FG_ELO,     f"{self.elo:>4} ({self.elo_matches})",
            COLOR_RESET
        ])


@dataclass
class EloChange:
    new_elo_1 : int
    new_elo_2 : int
    delta_elo_1 : int
    delta_elo_2 : int

    def __str__(self):
        BG_GRAY     = "\033[48;5;238m"
        FG_WHITE    = "\033[38;5;231m"
        FG_RED      = "\033[38;5;196m"
        FG_GREEN    = "\033[38;5;46m"
        COLOR_RESET = "\033[0;0m"
        return ''.join([
            BG_GRAY,
            FG_WHITE, f"{self.new_elo_1:>4}",
            FG_RED if self.delta_elo_1<0 else FG_GREEN, f"{f'[{self.delta_elo_1:+}]':>5} ",
            FG_WHITE, f"{self.new_elo_2:>4}",
            FG_RED if self.delta_elo_2<0 else FG_GREEN, f"{f'[{self.delta_elo_2:+}]':>5}",
            COLOR_RESET
        ])

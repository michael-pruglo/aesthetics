#!/usr/bin/env python3

from down_model import Usher
from secretcfg import USHER_CFG


if __name__ == "__main__":
  usher = Usher(USHER_CFG)

  catch_up = 3
  usher.process_recent_files(catch_up)

  usher.idle()

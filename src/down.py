#!/usr/bin/env python3

import logging
import sys

from down_model import Usher
from downcfg import USHER_CFG

logging.basicConfig(
  level = logging.INFO
)


if __name__ == "__main__":
  catch_up = int(sys.argv[1]) if len(sys.argv)>1 else 2
  Usher(USHER_CFG, catch_up).idle()

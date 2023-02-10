#!/usr/bin/env python3

import logging

from down_model import Usher
from downcfg import USHER_CFG

logging.basicConfig(
  level = logging.INFO
)


if __name__ == "__main__":
  Usher(USHER_CFG).idle()

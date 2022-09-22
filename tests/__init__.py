import os
import sys
import logging


PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(PROJECT_PATH, "src")
sys.path.append(SOURCE_PATH)

logging.disable(logging.CRITICAL)

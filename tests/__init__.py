import os
import sys
import logging


PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(PROJECT_PATH, "src")
sys.path.append(SOURCE_PATH)

MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
METAFILE = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
BACKUP_FOLDER = os.path.join(MEDIA_FOLDER, "bak/")
EXTRA_FOLDER = os.path.join(MEDIA_FOLDER, "extra/")

logging.disable(logging.CRITICAL)

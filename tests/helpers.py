import os


MEDIA_FOLDER = os.path.abspath("./tests/test_media/")
METAFILE = os.path.join(MEDIA_FOLDER, 'metadata_db.csv')
BACKUP_FOLDER = os.path.join(MEDIA_FOLDER, "bak/")
EXTRA_FOLDER = os.path.join(MEDIA_FOLDER, "extra/")


def get_initial_mediafiles() -> list[str]:
  return [f for f in os.listdir(MEDIA_FOLDER)
          if os.path.isfile(os.path.join(MEDIA_FOLDER, f))
          and f.split('.')[-1] != 'csv']

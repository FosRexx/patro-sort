import datetime
from pathlib import Path


class FileEntry:
    path: Path
    creation_date: datetime.datetime

    def __init__(self, path: Path, creation_date: datetime.datetime):
        self.path = path
        self.creation_date = creation_date

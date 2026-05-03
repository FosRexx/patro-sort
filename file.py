import datetime
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class FileType(Enum):
    IMAGE = auto()
    VIDEO = auto()
    AUDIO = auto()
    OTHER = auto()


def get_file_type(mime_type: Optional[str]) -> FileType:
    if mime_type is None:
        return FileType.OTHER
    if mime_type.startswith("image/"):
        return FileType.IMAGE
    if mime_type.startswith("video/"):
        return FileType.VIDEO
    if mime_type.startswith("audio/"):
        return FileType.AUDIO
    return FileType.OTHER


@dataclass
class FileEntry:
    path: Path
    type: FileType
    # UTC datetime; None means we could not determine a date
    ctime_utc: Optional[datetime.datetime]

    @property
    def is_sortable(self) -> bool:
        return self.type is not FileType.OTHER and self.ctime_utc is not None

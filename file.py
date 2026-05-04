"""
file.py - Core data types for file entries.

Defines the FileType enum and FileEntry dataclass used throughout patro-sort
to represent media files and their extracted metadata.
"""

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
    """
    Map a MIME type string to a FileType.

    Returns FileType.OTHER for None or any unrecognised prefix.
    """
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
    # UTC datetime; None means no creation date could be determined.
    ctime_utc: Optional[datetime.datetime]

    @property
    def is_sortable(self) -> bool:
        """
        True if the file can be placed in a dated folder.

        A file is sortable when it has a known media type (image, video, or
        audio) and a resolved creation date. Files of type OTHER or with a
        missing date are routed to the unsorted directory.
        """
        return self.type is not FileType.OTHER and self.ctime_utc is not None

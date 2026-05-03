import datetime
import logging
import sys
from pathlib import Path
from typing import Iterator, Optional

import dateutil
import statx
from exiftool.helper import ExifToolHelper

from file import FileEntry, get_file_type

logger = logging.getLogger(__name__)

BATCH_SIZE = 512
EXIFTOOL_CONFIG = str(Path(__file__).parent / "exif_comp_date.pl")


def _parse_date(utc_str: Optional[str]) -> Optional[datetime.datetime]:
    """Parse the Composite:MyDate ISO-8601 string returned by ExifTool."""
    if utc_str is None:
        return None

    try:
        dt: datetime.datetime = dateutil.parser.isoparse(utc_str)
        # Normalise to UTC-aware datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt
    except ValueError, OverflowError:
        logger.debug(f"Could not parse exif date string: {utc_str!r}")
        return None


def _get_fs_btime(file: Path) -> Optional[datetime.datetime]:
    """
    Return the best available filesystem creation/birth date as a UTC-aware
    datetime.
    """
    try:
        st = file.stat()
    except OSError:
        logger.debug(f"Could not get stat for {file}")
        return None

    try:
        btime = getattr(st, "st_birthtime")
    except AttributeError:
        # We're probably on Linux. Hopefully, we are on a recent enough
        # version that we can use the statx syscall. (If we are not, btime
        # below will be `None`.)
        logger.debug(
            "st_birthtime attribute error probably on Linux falling back to statx"
        )
        btime = statx.statx(file).btime

    if btime is None:
        return None
    else:
        return datetime.datetime.fromtimestamp(btime, tz=datetime.timezone.utc)


def _chunked(files: list[Path], size: int = BATCH_SIZE) -> Iterator[list[Path]]:
    for i in range(0, len(files), size):
        yield files[i : i + size]


def build_entries(files: list[Path]) -> Iterator[FileEntry]:
    """
    Yield FileEntry objects for every path, extracting creation dates via
    ExifTool first and falling back to filesystem timestamps.

    Processes files in batches for ExifTool performance; filesystem fallbacks
    are per-file and executed only when needed.
    """
    try:
        with ExifToolHelper(config_file=EXIFTOOL_CONFIG) as et:
            for batch in _chunked(files):
                for path, meta in zip(
                    batch, et.get_tags(batch, ["Composite:MyDate", "File:MIMEType"])
                ):
                    ctime_str: str | None = meta.get("Composite:MyDate")
                    mime_type: str | None = meta.get("File:MIMEType")

                    if mime_type is None:
                        logger.warning(
                            f"Could not get MIMEType of {path} treating it as unsortable"
                        )

                    ctime_utc = _parse_date(ctime_str) or _get_fs_btime(path)

                    if ctime_utc is None:
                        logger.warning(
                            f"Could not get creation time of {path} treating it as unsortable"
                        )

                    file = FileEntry(
                        path=path,
                        type=get_file_type(mime_type),
                        ctime_utc=ctime_utc,
                    )

                    yield file

    except FileNotFoundError:
        logger.critical(
            "ExifTool binary not found. Please install 'exiftool' on your system."
        )
        sys.exit(1)

    except Exception as e:
        logger.critical(f"Unexpected error during metadata extraction: {e}")
        sys.exit(1)

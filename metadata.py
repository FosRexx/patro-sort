"""
metadata.py - Extracts creation-date metadata from media files.

Uses ExifTool (via pyexiftool) to read a custom composite tag, MyDate, which
is defined in the accompanying exif_comp_date.pl config and resolves the most
meaningful creation timestamp across a wide range of EXIF, XMP, and IPTC
tags.

When ExifTool cannot supply a date and fs_ctime_fb is enabled, the function
falls back to the filesystem birth time (st_birthtime on macOS/BSD, or the
statx syscall on Linux).
"""

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


def _validate_config() -> None:
    """Abort early if the ExifTool config file is missing."""
    if not Path(EXIFTOOL_CONFIG).is_file():
        logger.critical("Required ExifTool config not found: %s", EXIFTOOL_CONFIG)
        sys.exit(1)


def _parse_date(utc_str: Optional[str]) -> Optional[datetime.datetime]:
    """
    Parse the Composite:MyDate ISO-8601 string returned by ExifTool.

    Returns a UTC-aware datetime, or None if the string is absent or
    unparseable.
    """
    if utc_str is None:
        return None

    try:
        dt: datetime.datetime = dateutil.parser.isoparse(utc_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            dt = dt.astimezone(datetime.timezone.utc)
        return dt
    except ValueError, OverflowError:
        logger.debug("Could not parse EXIF date string: %r", utc_str)
        return None


def _get_fs_btime(file: Path) -> Optional[datetime.datetime]:
    """
    Return the filesystem birth/creation time as a UTC-aware datetime.

    On macOS/BSD, uses st_birthtime from os.stat. On Linux, falls back to the
    statx syscall. Returns None if the time cannot be determined.
    """
    try:
        st = file.stat()
    except OSError as exc:
        logger.debug("Could not stat %s: %s", file, exc)
        return None

    btime: Optional[float] = getattr(st, "st_birthtime", None)

    if btime is None:
        # Linux path: st_birthtime is not available, try statx.
        logger.debug("st_birthtime not available for %s, falling back to statx.", file)
        btime = statx.statx(str(file)).btime

    if btime is None:
        logger.debug("statx returned no birth time for %s.", file)
        return None

    return datetime.datetime.fromtimestamp(btime, tz=datetime.timezone.utc)


def _chunked(files: list[Path], size: int = BATCH_SIZE) -> Iterator[list[Path]]:
    """Yield successive fixed-size chunks from files."""
    for i in range(0, len(files), size):
        yield files[i : i + size]


def build_entries(files: list[Path], fs_ctime_fb: bool = False) -> Iterator[FileEntry]:
    """
    Yield a FileEntry for every path in files.

    Metadata is extracted in batches via ExifTool for performance. For each
    file the function tries, in order:
      1. Composite:MyDate from ExifTool (preferred - most accurate).
      2. Filesystem birth time (only when fs_ctime_fb is True).

    If neither source produces a date, ctime_utc is set to None and the file
    will be treated as unsortable by the index.

    Args:
        files:       List of absolute paths to process.
        fs_ctime_fb: Enable filesystem birth-time fallback.

    Yields:
        FileEntry objects with path, type, and ctime_utc populated.
    """
    _validate_config()

    logger.debug(
        "Starting metadata extraction for %d file(s) (batch size: %d, "
        "filesystem fallback: %s).",
        len(files),
        BATCH_SIZE,
        fs_ctime_fb,
    )

    try:
        with ExifToolHelper(config_file=EXIFTOOL_CONFIG, check_execute=False) as et:
            for batch_index, batch in enumerate(_chunked(files), start=1):
                logger.debug(
                    "Processing ExifTool batch %d (%d file(s)).",
                    batch_index,
                    len(batch),
                )

                for path, meta in zip(
                    batch,
                    et.get_tags(batch, ["Composite:MyDate", "File:MIMEType"]),
                ):
                    ctime_str: Optional[str] = meta.get("Composite:MyDate")
                    mime_type: Optional[str] = meta.get("File:MIMEType")

                    if mime_type is None:
                        logger.warning(
                            "Could not determine MIME type for %s - treating as unsortable.",
                            path,
                        )

                    ctime_utc = _parse_date(ctime_str)

                    if ctime_utc is None and fs_ctime_fb:
                        logger.debug(
                            "No EXIF date for %s, trying filesystem birth time.", path
                        )
                        ctime_utc = _get_fs_btime(path)

                    if ctime_utc is None:
                        logger.warning(
                            "No creation date found for %s - treating as unsortable.",
                            path,
                        )
                    else:
                        logger.debug(
                            "Resolved creation time for %s: %s",
                            path,
                            ctime_utc.isoformat(),
                        )

                    yield FileEntry(
                        path=path,
                        type=get_file_type(mime_type),
                        ctime_utc=ctime_utc,
                    )

    except FileNotFoundError:
        logger.critical(
            "ExifTool binary not found. Please install 'exiftool' on your system."
        )
        sys.exit(1)

    except Exception as exc:
        logger.critical("Unexpected error during metadata extraction: %s", exc)
        sys.exit(1)

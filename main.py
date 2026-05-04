"""
main.py - Entry point for patro-sort.

patro-sort scans a source directory for media files (images, videos, audio),
extracts creation dates via ExifTool (with an optional filesystem fallback),
and organises them into a calendar-aware destination tree.

The default calendar system is Bikram Sambat (BS), producing folder and file
names expressed in the Nepali calendar. The underlying architecture supports
additional CalendarDateTime implementations without changes to this module.
"""

import logging
from pathlib import Path

from args import parse_args
from calendar_datetime import BikramSambatDateTime
from file_index import FileIndex
from metadata import build_entries
from sorted import sort_files

logger = logging.getLogger(__name__)


def _get_files_recursive(src_dir: Path) -> list[Path]:
    logger.info("Scanning %s recursively...", src_dir)
    files = [f for f in src_dir.rglob("*") if f.is_file()]
    logger.info("Found %d file(s) to evaluate.", len(files))
    logger.info("")
    return files


def _print_summary(index: FileIndex) -> None:
    s = index.stats
    logger.info("File scan summary:")
    logger.info("  Total   : %d", s.total)
    logger.info("  Images  : %d", s.images)
    logger.info("  Videos  : %d", s.videos)
    logger.info("  Audio   : %d", s.audio)
    logger.info("  Other   : %d", s.other)
    logger.info("")

    if s.other:
        logger.info(
            "%d file(s) are in an unrecognised format and will be placed in "
            "dest_dir/unsorted/ without date-based sorting.",
            s.other,
        )

    no_date = sum(1 for e in index.unsortable if e.ctime_utc is None)
    if no_date:
        logger.info(
            "%d file(s) had no detectable creation date and will also be "
            "placed in dest_dir/unsorted/.",
            no_date,
        )

    if s.other or no_date:
        logger.info("")


def _log_final_result(result) -> None:
    separator = "=" * 72
    logger.info(separator)
    logger.info("Sort complete.")
    logger.info("  Hard-linked : %d", result.linked)
    logger.info("  Copied      : %d", result.copied)
    logger.info("  Unsorted    : %d", result.unsorted)
    logger.info("  Errors      : %d", result.errors)
    logger.info(separator)

    if result.errors:
        logger.warning(
            "%d error(s) occurred - review the log above for details.",
            result.errors,
        )


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    logger.info("patro-sort")
    logger.info("Source      : %s", args.src_dir)
    logger.info("Destination : %s", args.dest_dir)
    logger.info("Calendar    : Bikram Sambat (BS)")
    logger.info(
        "Mode        : %s", "dry-run (no files written)" if args.dry_run else "wet-run"
    )
    logger.info("")

    files = _get_files_recursive(args.src_dir)

    if not files:
        logger.warning("No files found in %s. Nothing to do.", args.src_dir)
        return

    index = FileIndex(BikramSambatDateTime)
    logger.info("Extracting metadata...")

    for entry in build_entries(files, args.fs_ctime_fb):
        index.add(entry)
        logger.debug("")

    logger.info("")

    _print_summary(index)

    logger.info("Sorting files...")
    result = sort_files(index, args.dest_dir, args.dry_run)
    _log_final_result(result)


if __name__ == "__main__":
    main()

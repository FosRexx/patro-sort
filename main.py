import logging
from pathlib import Path

from args import parse_args
from calendar_datetime import BikramSambatDateTime
from file_index import FileIndex
from metadata import build_entries

logger = logging.getLogger(__name__)


def _get_files_recursive(src_dir: Path) -> list[Path]:
    logger.info(f"Scanning {src_dir} recursively...")
    logger.info("")

    files = [f for f in src_dir.rglob("*") if f.is_file()]

    return files


def _print_summary(index: FileIndex) -> None:
    s = index.stats
    print(f"Found {s.total} files total:")
    print(f"  Images : {s.images}")
    print(f"  Videos : {s.videos}")
    print(f"  Audio  : {s.audio}")
    print(f"  Other  : {s.other}")
    print()

    if s.other:
        print(
            f"{s.other} file(s) are in an unrecognised format and will be "
            f"placed in dest_dir/unsorted/ without sorting."
        )

    no_date = sum(1 for e in index.unsortable if e.ctime_utc is None)
    if no_date:
        print(
            f"{no_date} file(s) had no detectable creation date and will "
            f"also be placed in dest_dir/unsorted/."
        )
    print()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    logger.info(f"Starting sort: {args.src_dir} -> {args.dest_dir}")
    logger.info("")

    files = _get_files_recursive(args.src_dir)

    if not files:
        logger.warning("No files found to process.")
        return

    index = FileIndex(BikramSambatDateTime)

    for entry in build_entries(files):
        index.add(entry)

    _print_summary(index)


if __name__ == "__main__":
    main()

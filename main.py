import argparse
import logging
import mimetypes
from pathlib import Path
from typing import List

mimetypes.init()

logger = logging.getLogger(__name__)


def get_media_creation_date(file: Path):
    pass


def is_media_file(file: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(file)
    if mime_type:
        return mime_type.startswith(("image/", "video/"))
    return False


def get_media_files(src_dir: Path) -> List[Path]:
    logger.info(f"Scanning directory: {src_dir}")
    logger.info("")

    media_files = [f for f in src_dir.rglob("*") if f.is_file() and is_media_file(f)]

    logger.info(f"Found {len(media_files)} candidate media files.")
    return media_files


class Args(argparse.Namespace):
    src_dir: Path
    dest_dir: Path
    debug: bool


def validate_args(args: Args, parser: argparse.ArgumentParser) -> None:
    if not args.src_dir.is_dir():
        parser.error(f"Source directory does not exists: {args.src_dir}")

    if args.src_dir.resolve() == args.dest_dir.resolve():
        parser.error("Source and destination directories cannot be the same.")

    if args.dest_dir.exists():
        if not args.dest_dir.is_dir():
            parser.error(f"Destination path not a directory: {args.dest_dir}")

        dest_dir_not_empty = any(args.dest_dir.iterdir())

        if dest_dir_not_empty:
            parser.error(f"Destination directory must be empty: {args.dest_dir}")


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        prog="bs-media-sorter",
        description="Sort images/videos into Bikram Samvat (BS) folder structures.",
    )

    parser.add_argument("src_dir", type=Path, help="Source directory containing media")
    parser.add_argument("dest_dir", type=Path, help="Destination for sorted media")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args(namespace=Args())

    validate_args(args, parser)

    return args


def main() -> None:
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logger.info(f"Starting sort: {args.src_dir} -> {args.dest_dir}")
    logger.info("")

    media_files = get_media_files(args.src_dir)

    if not media_files:
        logger.warning("No media files found to process.")
        return


if __name__ == "__main__":
    main()

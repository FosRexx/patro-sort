import argparse
from pathlib import Path


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

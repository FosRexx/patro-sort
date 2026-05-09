"""
args.py - Command-line argument parsing and validation for patro-sort.
"""

import argparse
from pathlib import Path


class Args(argparse.Namespace):
    src_dir: Path
    dest_dir: Path
    verbose: bool
    dry_run: bool
    fs_ctime_fb: bool  # filesystem creation-time fallback
    fn_inc_year: bool  # filename include year


def validate_args(args: Args, parser: argparse.ArgumentParser) -> None:
    """
    Validate parsed arguments and call parser.error() on any violation.

    Checks:
      - src_dir must exist and be a directory.
      - src_dir and dest_dir must not resolve to the same path.
      - dest_dir, if it exists, must be an empty directory.
    """
    if not args.src_dir.is_dir():
        parser.error(f"Source directory does not exist: {args.src_dir}")

    if args.src_dir.resolve() == args.dest_dir.resolve():
        parser.error("Source and destination directories cannot be the same.")

    if args.dest_dir.exists():
        if not args.dest_dir.is_dir():
            parser.error(f"Destination path is not a directory: {args.dest_dir}")

        if any(args.dest_dir.iterdir()):
            parser.error(f"Destination directory must be empty: {args.dest_dir}")


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        prog="patro-sort",
        description=(
            "Sort media files (images, videos, audio) into a Bikram Sambat "
            "calendar folder structure. Files are renamed to their creation "
            "timestamp and organised by BS year and month."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "src_dir",
        type=Path,
        help="Source directory to scan for media files (searched recursively).",
    )
    parser.add_argument(
        "dest_dir",
        type=Path,
        help="Destination directory for the sorted output (must be empty or absent).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "-w",
        "--wet-run",
        action="store_false",
        dest="dry_run",
        help=(
            "Perform the sort for real. By default the program runs in dry-run "
            "mode and only logs what it would do without writing any files."
        ),
    )
    parser.add_argument(
        "--fs-ctime-fb",
        action="store_true",
        dest="fs_ctime_fb",
        help=(
            "Fall back to the filesystem birth time when ExifTool cannot "
            "supply a creation date."
        ),
    )
    parser.add_argument(
        "--fn-inc-year",
        action="store_true",
        dest="fn_inc_year",
        help="Should the dest media filename include year",
    )

    args = parser.parse_args(namespace=Args())

    validate_args(args, parser)

    return args

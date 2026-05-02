import logging
from pathlib import Path
from typing import List

from exiftool.helper import ExifToolHelper

from args import parse_args

logger = logging.getLogger(__name__)


def get_files_recursive(src_dir: Path) -> List[Path]:
    logger.info(f"Scanning directory {src_dir} recursively")
    logger.info("")

    files = [f for f in src_dir.rglob("*") if f.is_file()]

    return files


def main() -> None:
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logger.info(f"Starting sort: {args.src_dir} -> {args.dest_dir}")
    logger.info("")

    files = get_files_recursive(args.src_dir)
    no_of_files = len(files)

    if no_of_files == 0:
        logger.warning("No files found to process.")
        return
    else:
        logger.info(f"Found {no_of_files} files.")

    try:
        with ExifToolHelper() as et:
            pass
    except FileNotFoundError:
        logger.critical(
            "ExifTool binary not found. Please install 'exiftool' on your system."
        )
    except Exception as e:
        logger.critical(f"A terminal error occurred: {e}")


if __name__ == "__main__":
    main()

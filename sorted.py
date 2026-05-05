"""
sorted.py - Materialises the sorted destination directory tree.

Files are organised as:
    <dest_dir>/<year>/<month_two_digit>/<calendar_timestamp><ext>

The year, month, and timestamp all derive from the same CalendarDateTime
instance, so folder names and filenames are always expressed in the same
calendar system.

Unsortable files (unknown type or missing date) are placed under:
    <dest_dir>/unsorted/<relative_path_from_src_dir>

Preserving the relative path means the original folder structure is retained
under the unsorted directory, making it easy to locate files manually.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from calendar_datetime import CalendarDateTime
from file_index import FileIndex

logger = logging.getLogger(__name__)

UNSORTED_DIR_NAME = "unsorted"


@dataclass
class SortResult:
    linked: int = 0
    copied: int = 0
    unsorted: int = 0
    errors: int = 0

    @property
    def total_processed(self) -> int:
        return self.linked + self.copied + self.unsorted

    @property
    def total_errors(self) -> int:
        return self.errors


def _dest_filename(cdt: CalendarDateTime, original_suffix: str) -> str:
    """
    Build an ISO-8601-ish filename from a CalendarDateTime.

    The timestamp reflects the calendar system and timezone of the cdt
    instance (e.g. BS year + NST time for BikramSambatDateTime). Colons are
    replaced with hyphens for cross-platform filesystem compatibility.

    Examples:
        BS  : 2081-04-15T10-30-00+0545.jpg
        UTC : 2024-07-30T04-45-00+0000.jpg
    """
    return f"{cdt.isoformat_filename_safe()}{original_suffix.lower()}"


def _unique_dest(dest_dir: Path, filename: str) -> Path:
    """
    Return a destination path that does not collide with any existing file.

    If <dest_dir>/<filename> already exists, appends an incrementing counter
    suffix: <stem>_1<ext>, <stem>_2<ext>, etc.
    """
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _link(src: Path, dest: Path) -> bool:
    """
    Attempt a hard link from src to dest.

    Returns True on success, False if the filesystem does not support hard
    links (cross-device or unsupported), in which case the caller should fall
    back to a copy.
    """
    try:
        os.link(src, dest)
        return True
    except OSError:
        return False


def _batch_link_or_copy(
    pairs: list[tuple[Path, Path]],
    dry_run: bool,
) -> tuple[int, int, int]:
    """
    Hard-link or copy a batch of (src, dest) pairs.

    Tries os.link for every file in the batch first. If linking fails for any
    pair (e.g. cross-device), falls back to shutil.copy2 for that pair only.

    Returns (linked, copied, errors) counts for the batch.
    """
    linked = 0
    copied = 0
    errors = 0

    for src, dest in pairs:
        if dry_run:
            # In dry-run mode we count everything as "would link" and skip I/O.
            linked += 1
            continue

        try:
            if _link(src, dest):
                linked += 1
            else:
                shutil.copy2(src, dest)
                copied += 1
        except Exception as exc:
            logger.warning("Failed to place %s -> %s: %s", src, dest, exc)
            errors += 1

    return linked, copied, errors


def _log_batch_summary(
    period_label: str,
    triples: list[tuple[Path, Path, str]],
    dry_run: bool,
) -> None:
    """
    Emit a human-readable block for one year-month batch.

    Each line shows: <original filename> -> <dest path>  [action]
    The period_label (e.g. "2081/04") acts as a section header.
    """
    prefix = "[dry-run] " if dry_run else ""
    separator = "-" * 72
    logger.info(separator)
    logger.info("%sBatch: %s  (%d file(s))", prefix, period_label, len(triples))
    logger.info(separator)
    for src, dest, action in triples:
        logger.info("  [%-8s]  %s  ->  %s", action, src.name, dest)
    logger.info("")


def sort_files(index: FileIndex, dest_dir: Path, dry_run: bool = True) -> SortResult:
    """
    Materialise the destination directory tree from the given FileIndex.

    Each year-month group is processed as a single batch: destination paths
    are resolved first, then all hard-links (or copies) for that batch are
    performed together. This avoids per-file overhead and keeps the log output
    grouped by period.

    Args:
        index:    Populated FileIndex whose calendar_factory determines the
                  folder/filename calendar system.
        dest_dir: Root of the destination tree (created if absent).
        dry_run:  When True, logs what would happen but performs no I/O.

    Returns:
        SortResult with counts of linked, copied, unsorted, and errored files.
    """
    if dry_run:
        logger.info("Dry-run mode enabled - no files will be written.")
        logger.info("")

    result = SortResult()

    for year in index.years():
        for month in index.months_for_year(year):
            entries = index.entries_for_period(year, month)
            if not entries:
                continue

            period_label = f"{year}/{month:02d}"
            period_dir = dest_dir / period_label

            if not dry_run:
                period_dir.mkdir(parents=True, exist_ok=True)
                logger.debug("Created directory: %s", period_dir)

            # Resolve all destination paths for this batch before any I/O.
            pairs: list[tuple[Path, Path]] = []
            resolved_triples: list[tuple[Path, Path, str]] = []

            for entry in entries:
                assert entry.ctime_utc is not None
                try:
                    cdt = index.calendar_factory(entry.ctime_utc)
                    filename = _dest_filename(cdt, entry.path.suffix)
                    dest_path = _unique_dest(period_dir, filename)
                    pairs.append((entry.path, dest_path))
                    resolved_triples.append((entry.path, dest_path, "pending"))
                except Exception as exc:
                    logger.warning(
                        "Skipping %s - could not resolve destination: %s",
                        entry.path,
                        exc,
                    )
                    result.errors += 1

            # Perform the batch operation.
            linked, copied, errors = _batch_link_or_copy(pairs, dry_run)
            result.linked += linked
            result.copied += copied
            result.errors += errors

            # Annotate each log entry with its actual outcome.
            # _batch_link_or_copy processes pairs in order: links first, then
            # copies on fallback, so we can reconstruct per-file actions by
            # counting down the returned totals.
            annotated: list[tuple[Path, Path, str]] = []
            link_budget = linked
            copy_budget = copied
            for src, dest, _ in resolved_triples:
                if link_budget > 0:
                    annotated.append((src, dest, "linked"))
                    link_budget -= 1
                elif copy_budget > 0:
                    annotated.append((src, dest, "copied"))
                    copy_budget -= 1
                else:
                    annotated.append((src, dest, "error"))

            _log_batch_summary(period_label, annotated, dry_run)

    # Place unsortable files under <dest_dir>/unsorted/, preserving their
    # relative path within the source tree. For example, a file originally at
    # <src_dir>/foo/bar.jpg lands at <dest_dir>/unsorted/foo/bar.jpg.
    if index.unsortable:
        unsorted_base = dest_dir / UNSORTED_DIR_NAME

        unsorted_pairs: list[tuple[Path, Path]] = []
        unsorted_log: list[tuple[Path, Path, str]] = []

        for entry in index.unsortable:
            rel = index.relative_path(entry)
            dest_path = _unique_dest(unsorted_base / rel.parent, rel.name)
            if not dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                logger.debug("Created directory: %s", dest_path.parent)
            unsorted_pairs.append((entry.path, dest_path))
            unsorted_log.append((entry.path, dest_path, "unsorted"))

        _batch_link_or_copy(unsorted_pairs, dry_run)
        result.unsorted += len(unsorted_pairs)

        _log_batch_summary("unsorted", unsorted_log, dry_run)

    return result

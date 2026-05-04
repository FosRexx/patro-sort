"""
file_index.py - Calendar-agnostic registry for FileEntry objects.

FileIndex accepts a calendar_factory callable that converts a UTC datetime
into a CalendarDateTime subclass. All year/month bucketing is performed in
whatever calendar system the factory produces, so the same index can power
both Gregorian and Bikram Sambat sorting without code changes.
"""

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from calendar_datetime import CalendarDateTime
from file import FileEntry, FileType

logger = logging.getLogger(__name__)

CalendarFactory = Callable[..., CalendarDateTime]


@dataclass
class CategoryStats:
    images: int = 0
    videos: int = 0
    audio: int = 0
    other: int = 0

    @property
    def total(self) -> int:
        return self.images + self.videos + self.audio + self.other

    @property
    def sortable(self) -> int:
        """Number of files that can be placed in a dated folder."""
        return self.images + self.videos + self.audio


@dataclass
class FileIndex:
    """
    Calendar-agnostic registry for FileEntry objects.

    Files are bucketed by (year, month) in the calendar produced by
    calendar_factory. Files that cannot be sorted (unknown type or missing
    date, or a date that falls outside the calendar's supported range) are
    collected in the unsortable list.

    Args:
        calendar_factory: A callable that accepts a UTC datetime and returns
                          a CalendarDateTime instance. Typically a subclass
                          constructor, e.g. BikramSambatDateTime.
    """

    calendar_factory: CalendarFactory

    _entries: list[FileEntry] = field(default_factory=list, init=False)
    # (year, month) in the chosen calendar → sortable entries
    _by_period: dict[tuple[int, int], list[FileEntry]] = field(
        default_factory=lambda: defaultdict(list), init=False
    )
    _unsortable: list[FileEntry] = field(default_factory=list, init=False)
    _stats: CategoryStats = field(default_factory=CategoryStats, init=False)

    def add(self, entry: FileEntry) -> None:
        """
        Register a FileEntry in the index.

        If the entry is not sortable (wrong type or missing date), it is
        appended to the unsortable list. Otherwise it is bucketed by the
        (year, month) returned by the calendar_factory. Dates that fall
        outside the calendar's supported range are also treated as unsortable.
        """
        self._entries.append(entry)
        self._update_stats(entry)

        if not entry.is_sortable:
            logger.debug(
                "Marking %s as unsortable (type=%s, has_date=%s).",
                entry.path,
                entry.type.name,
                entry.ctime_utc is not None,
            )
            self._unsortable.append(entry)
            return

        try:
            cdt = self.calendar_factory(entry.ctime_utc)
            self._by_period[(cdt.year, cdt.month)].append(entry)
            logger.debug(
                "Indexed %s -> period %04d/%02d.", entry.path, cdt.year, cdt.month
            )
        except (ValueError, Exception) as exc:
            logger.warning(
                "Could not convert date for %s to the target calendar (%s) "
                "- treating as unsortable.",
                entry.path,
                exc,
            )
            self._unsortable.append(entry)

    def _update_stats(self, entry: FileEntry) -> None:
        match entry.type:
            case FileType.IMAGE:
                self._stats.images += 1
            case FileType.VIDEO:
                self._stats.videos += 1
            case FileType.AUDIO:
                self._stats.audio += 1
            case FileType.OTHER:
                self._stats.other += 1

    @property
    def stats(self) -> CategoryStats:
        return self._stats

    @property
    def all_entries(self) -> list[FileEntry]:
        return self._entries

    @property
    def unsortable(self) -> list[FileEntry]:
        return self._unsortable

    def years(self) -> list[int]:
        """Sorted list of distinct years (in the target calendar) present in the index."""
        return sorted({year for year, _ in self._by_period})

    def months_for_year(self, year: int) -> list[int]:
        """Sorted list of distinct months present for the given year."""
        return sorted({month for y, month in self._by_period if y == year})

    def entries_for_period(self, year: int, month: int) -> list[FileEntry]:
        """Return all sortable entries for the given year-month pair."""
        return self._by_period.get((year, month), [])

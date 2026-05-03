from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from calendar_datetime import CalendarDateTime
from file import FileEntry, FileType

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
        return self.images + self.videos + self.audio


@dataclass
class FileIndex:
    """
    Calendar-agnostic registry for FileEntry objects.

    Accepts a `calendar_factory`.
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
        self._entries.append(entry)
        self._update_stats(entry)

        if not entry.is_sortable:
            self._unsortable.append(entry)
            return

        try:
            cdt = self.calendar_factory(entry.ctime_utc)
            self._by_period[(cdt.year, cdt.month)].append(entry)
        except ValueError, Exception:
            # Date outside supported calendar range → treat as unsortable
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
        """Sorted list of distinct years (in the chosen calendar) present in the index."""
        return sorted({year for year, _ in self._by_period})

    def months_for_year(self, year: int) -> list[int]:
        """Sorted list of distinct months present for the given year."""
        return sorted({month for y, month in self._by_period if y == year})

    def entries_for_period(self, year: int, month: int) -> list[FileEntry]:
        return self._by_period.get((year, month), [])

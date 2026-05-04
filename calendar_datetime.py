"""
calendar_datetime.py - Abstract and concrete CalendarDateTime implementations.

CalendarDateTime wraps a UTC datetime and exposes it as year/month/day/time
components in a specific calendar system and timezone. Subclasses handle the
conversion; the rest of the codebase is calendar-agnostic.

Provided implementations:
    BikramSambatDateTime - Nepali Bikram Sambat calendar, Nepal Standard Time
                           (UTC+05:45).
"""

import datetime
from abc import ABC, abstractmethod

import nepali_datetime


class CalendarDateTime(ABC):
    """
    A point in time expressed in a specific calendar system and timezone.

    Concrete subclasses convert a UTC datetime into their own representation
    and expose year/month/day/time components for directory naming and
    filename generation.
    """

    def __init__(self, utc: datetime.datetime) -> None:
        # Ensure the stored value is always UTC-aware.
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=datetime.timezone.utc)
        self._utc = utc

    @property
    def utc(self) -> datetime.datetime:
        """The original UTC datetime this instance was constructed from."""
        return self._utc

    @property
    @abstractmethod
    def year(self) -> int: ...

    @property
    @abstractmethod
    def month(self) -> int: ...

    @property
    @abstractmethod
    def day(self) -> int: ...

    @property
    @abstractmethod
    def hour(self) -> int: ...

    @property
    @abstractmethod
    def minute(self) -> int: ...

    @property
    @abstractmethod
    def second(self) -> int: ...

    @property
    @abstractmethod
    def utc_offset_str(self) -> str:
        """
        UTC offset formatted for use in filenames, e.g. '+0545' or '+0000'.

        Colons are intentionally omitted because they are illegal in filenames
        on Windows.
        """
        ...

    def isoformat_filename_safe(self) -> str:
        """
        Return an ISO-8601-ish timestamp safe to use as a filename component.

        Format: YYYY-MM-DDTHH-MM-SS<utc_offset_str>

        Colons within the time portion are replaced with hyphens for
        cross-platform filesystem compatibility.
        """
        return (
            f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
            f"T{self.hour:02d}-{self.minute:02d}-{self.second:02d}"
            f"{self.utc_offset_str}"
        )


class BikramSambatDateTime(CalendarDateTime):
    """
    CalendarDateTime expressed in the Bikram Sambat calendar, Nepal Standard
    Time (NST, UTC+05:45).

    Date components (year, month, day) are in the BS calendar. Time components
    (hour, minute, second) reflect NST. The UTC offset string is always
    '+0545'.
    """

    def __init__(self, utc: datetime.datetime) -> None:
        super().__init__(utc)
        self._nst = self._utc.astimezone(
            datetime.timezone(datetime.timedelta(hours=5, minutes=45))
        )
        nsd: nepali_datetime.date = nepali_datetime.date.from_datetime_date(
            self._nst.date()
        )

        self._bs_year = nsd.year
        self._bs_month = nsd.month
        self._bs_day = nsd.day

    @property
    def year(self) -> int:
        return self._bs_year

    @property
    def month(self) -> int:
        return self._bs_month

    @property
    def day(self) -> int:
        return self._bs_day

    @property
    def hour(self) -> int:
        return self._nst.hour

    @property
    def minute(self) -> int:
        return self._nst.minute

    @property
    def second(self) -> int:
        return self._nst.second

    @property
    def utc_offset_str(self) -> str:
        return "+0545"

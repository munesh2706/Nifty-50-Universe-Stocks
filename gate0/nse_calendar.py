"""NSE session calendar (Gate 0 harness, Phase A).

Deterministic, repository-only. No network, no provider calls, no live data.
Models regular NSE session boundaries, trading-day/holiday/weekend logic, early
closes, and the expected completed 5m/15m bar-start slots for a session
(spec v0.2 §4). Holiday/early-close data is a **versioned local input**; this
module is NOT an authoritative or auto-current source — the supplied data must be
separately sourced and audited before any real use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from types import MappingProxyType
from typing import Mapping

from gate0.canonical_bars import IST, TIMEFRAME_MINUTES

REGULAR_OPEN = time(9, 15)
REGULAR_CLOSE = time(15, 30)
WEEKEND = {5, 6}  # Mon=0 ... Sat=5, Sun=6


class CalendarValidationError(ValueError):
    """Raised when a CalendarData input is malformed. Fail-closed (C2)."""


@dataclass(frozen=True)
class CalendarData:
    """Versioned local calendar input. `holidays` and `early_closes` are supplied,
    not discovered. `version`/`source` document provenance for the audit trail.

    Validated on construction (fail-closed): non-empty version/source, open earlier
    than close, and every early close strictly after that day's open and no later
    than the regular close.
    """

    version: str
    source: str
    holidays: frozenset[date] = field(default_factory=frozenset)
    early_closes: Mapping[date, time] = field(default_factory=dict)  # date -> early close time
    open_time: time = REGULAR_OPEN
    close_time: time = REGULAR_CLOSE

    def __post_init__(self) -> None:
        # C3: defensively copy caller-supplied collections into immutable forms so
        # that later mutation of the caller's originals (or of our attributes)
        # cannot change classifications after validation.
        object.__setattr__(self, "holidays", frozenset(self.holidays))
        object.__setattr__(self, "early_closes", MappingProxyType(dict(self.early_closes)))

        if not (self.version and self.version.strip()):
            raise CalendarValidationError("version must be a non-empty provenance string")
        if not (self.source and self.source.strip()):
            raise CalendarValidationError("source must be a non-empty provenance string")
        if self.open_time >= self.close_time:
            raise CalendarValidationError(
                f"regular open {self.open_time} must be earlier than close {self.close_time}"
            )
        for d, ec in self.early_closes.items():
            if ec <= self.open_time:
                raise CalendarValidationError(f"early close {ec} on {d} must be after open {self.open_time}")
            if ec > self.close_time:
                raise CalendarValidationError(
                    f"early close {ec} on {d} must be no later than regular close {self.close_time}"
                )


# A clearly-labelled SAMPLE for tests/dev only. NOT authoritative NSE data.
SAMPLE_CALENDAR = CalendarData(
    version="sample-0",
    source="SYNTHETIC SAMPLE — not authoritative; replace with audited NSE data",
    holidays=frozenset({date(2026, 11, 5)}),          # synthetic holiday
    early_closes={date(2026, 11, 6): time(13, 0)},     # synthetic early close
)


class TradingCalendar:
    def __init__(self, data: CalendarData) -> None:
        # C1: no implicit default. The caller must supply explicit, audited
        # CalendarData; the synthetic SAMPLE_CALENDAR is never selected silently.
        if not isinstance(data, CalendarData):
            raise CalendarValidationError("TradingCalendar requires an explicit CalendarData")
        self.data = data

    def is_trading_day(self, d: date) -> bool:
        return d.weekday() not in WEEKEND and d not in self.data.holidays

    def session_bounds(self, d: date) -> tuple[datetime, datetime] | None:
        """(open_dt, close_dt) in IST for a trading day, honoring early close; else None."""
        if not self.is_trading_day(d):
            return None
        open_dt = datetime.combine(d, self.data.open_time, tzinfo=IST)
        close_t = self.data.early_closes.get(d, self.data.close_time)
        close_dt = datetime.combine(d, close_t, tzinfo=IST)
        return open_dt, close_dt

    def expected_bar_starts(self, d: date, timeframe: str) -> list[datetime]:
        """Bar-start timestamps of every COMPLETED bar in the session.

        A bar counts only if it fully closes within the session (start + tf <= close).
        Empty list for non-trading days or unknown timeframe.
        """
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        bounds = self.session_bounds(d)
        if minutes is None or bounds is None:
            return []
        open_dt, close_dt = bounds
        step = timedelta(minutes=minutes)
        starts: list[datetime] = []
        cur = open_dt
        while cur + step <= close_dt:
            starts.append(cur)
            cur += step
        return starts

    def expected_bar_count(self, d: date, timeframe: str) -> int:
        return len(self.expected_bar_starts(d, timeframe))

    def is_aligned(self, ts: datetime, timeframe: str) -> bool:
        """True if ts is a valid completed bar-start slot for its date/timeframe."""
        minutes = TIMEFRAME_MINUTES.get(timeframe)
        if minutes is None or ts.tzinfo is None:
            return False
        return ts.astimezone(IST) in set(self.expected_bar_starts(ts.astimezone(IST).date(), timeframe))

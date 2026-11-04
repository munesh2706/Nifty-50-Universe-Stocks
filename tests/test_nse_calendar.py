"""Phase A unit tests for nse_calendar. Synthetic/sample data only; no network."""
from __future__ import annotations

from datetime import date, datetime, time

import pytest

from gate0.canonical_bars import IST
from gate0.nse_calendar import (
    SAMPLE_CALENDAR,
    CalendarData,
    CalendarValidationError,
    TradingCalendar,
)

CAL = TradingCalendar(SAMPLE_CALENDAR)

# 2026-11-04 is a Wednesday (normal trading day in the sample).
NORMAL = date(2026, 11, 4)
HOLIDAY = date(2026, 11, 5)       # synthetic holiday in SAMPLE_CALENDAR
EARLY = date(2026, 11, 6)         # synthetic early close 13:00
SATURDAY = date(2026, 11, 7)
SUNDAY = date(2026, 11, 8)


def test_normal_trading_day():
    assert CAL.is_trading_day(NORMAL)


def test_weekend_not_trading():
    assert not CAL.is_trading_day(SATURDAY)
    assert not CAL.is_trading_day(SUNDAY)


def test_holiday_not_trading():
    assert not CAL.is_trading_day(HOLIDAY)


def test_session_bounds_regular():
    o, c = CAL.session_bounds(NORMAL)
    assert o == datetime(2026, 11, 4, 9, 15, tzinfo=IST)
    assert c == datetime(2026, 11, 4, 15, 30, tzinfo=IST)


def test_session_bounds_none_on_holiday():
    assert CAL.session_bounds(HOLIDAY) is None


def test_expected_bar_counts_regular():
    # 09:15..15:30 = 375 minutes -> 75 x 5m, 25 x 15m completed bars.
    assert CAL.expected_bar_count(NORMAL, "5m") == 75
    assert CAL.expected_bar_count(NORMAL, "15m") == 25


def test_first_and_last_slots_regular():
    starts5 = CAL.expected_bar_starts(NORMAL, "5m")
    assert starts5[0] == datetime(2026, 11, 4, 9, 15, tzinfo=IST)
    assert starts5[-1] == datetime(2026, 11, 4, 15, 25, tzinfo=IST)  # closes at 15:30
    starts15 = CAL.expected_bar_starts(NORMAL, "15m")
    assert starts15[-1] == datetime(2026, 11, 4, 15, 15, tzinfo=IST)  # closes at 15:30


def test_early_close_reduces_slots():
    # 09:15..13:00 = 225 minutes -> 45 x 5m, 15 x 15m.
    assert CAL.expected_bar_count(EARLY, "5m") == 45
    assert CAL.expected_bar_count(EARLY, "15m") == 15
    assert CAL.expected_bar_starts(EARLY, "5m")[-1] == datetime(2026, 11, 6, 12, 55, tzinfo=IST)


def test_holiday_and_weekend_have_no_slots():
    assert CAL.expected_bar_starts(HOLIDAY, "5m") == []
    assert CAL.expected_bar_starts(SATURDAY, "15m") == []


def test_unknown_timeframe_empty():
    assert CAL.expected_bar_starts(NORMAL, "1m") == []


def test_alignment():
    assert CAL.is_aligned(datetime(2026, 11, 4, 9, 30, tzinfo=IST), "15m")
    assert not CAL.is_aligned(datetime(2026, 11, 4, 9, 17, tzinfo=IST), "5m")      # off-grid
    assert not CAL.is_aligned(datetime(2026, 11, 4, 15, 30, tzinfo=IST), "5m")     # session end, no completed bar starts here
    assert not CAL.is_aligned(datetime(2026, 11, 5, 9, 15, tzinfo=IST), "5m")      # holiday


def test_custom_calendar_data_version_recorded():
    data = CalendarData(version="test-1", source="unit")
    cal = TradingCalendar(data)
    assert cal.data.version == "test-1"
    # No holidays supplied -> a normal weekday trades.
    assert cal.is_trading_day(NORMAL)


# --- C1: no silent synthetic default ---

def test_trading_calendar_requires_explicit_data():
    with pytest.raises(TypeError):
        TradingCalendar()  # type: ignore[call-arg]


def test_sample_calendar_must_be_passed_explicitly():
    # Using the sample requires an explicit choice; it is never the default.
    cal = TradingCalendar(SAMPLE_CALENDAR)
    assert cal.data is SAMPLE_CALENDAR


# --- C2: fail-closed config validation ---

def test_empty_version_rejected():
    with pytest.raises(CalendarValidationError):
        CalendarData(version="", source="unit")


def test_empty_source_rejected():
    with pytest.raises(CalendarValidationError):
        CalendarData(version="v", source="  ")


def test_invalid_regular_bounds_rejected():
    with pytest.raises(CalendarValidationError):
        CalendarData(version="v", source="s", open_time=time(15, 30), close_time=time(9, 15))


def test_early_close_before_open_rejected():
    with pytest.raises(CalendarValidationError):
        CalendarData(version="v", source="s", early_closes={date(2026, 11, 6): time(9, 0)})


def test_early_close_after_regular_close_rejected():
    with pytest.raises(CalendarValidationError):
        CalendarData(version="v", source="s", early_closes={date(2026, 11, 6): time(16, 0)})

"""Phase A unit tests for canonical bar validation + 5m->15m aggregation.

Synthetic fixtures only; no provider contact. Covers review items R1-R6.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from gate0.canonical_bars import IST, Bar, aggregate_5m_to_15m, validate_bar, validate_series
from gate0.fixtures.synthetic_bars import make_5m_run, make_bar

NAN = float("nan")
INF = float("inf")


# --- baseline validity ---

def test_valid_bar_has_no_problems():
    assert validate_bar(make_bar()) == []


def test_clean_run_ok():
    assert validate_series(make_5m_run(6)) == []


# --- §3.3 OHLC / volume ---

def test_high_not_max_detected():
    assert "HIGH_NOT_MAX" in validate_bar(make_bar(o=100, h=100.4, low=99, c=100.5))


def test_low_not_min_detected():
    assert "LOW_NOT_MIN" in validate_bar(make_bar(o=100, h=101, low=100.2, c=99.5))


def test_non_positive_price_detected():
    assert "NON_POSITIVE_PRICE" in validate_bar(make_bar(o=0, h=1, low=0, c=0.5))


def test_negative_volume_detected():
    assert "NEGATIVE_VOLUME" in validate_bar(make_bar(volume=-1))


def test_empty_instrument_id_detected():
    assert "EMPTY_INSTRUMENT_ID" in validate_bar(make_bar(instrument_id=""))


# --- R1 non-finite ---

def test_nan_in_each_field_rejected():
    for kw in ("o", "h", "low", "c", "volume"):
        bar = make_bar(**{kw: NAN})
        assert "NON_FINITE_VALUE" in validate_bar(bar), kw


def test_inf_rejected():
    assert "NON_FINITE_VALUE" in validate_bar(make_bar(h=INF))
    assert "NON_FINITE_VALUE" in validate_bar(make_bar(low=-INF))


# --- R2 completed-bar contract ---

def test_incomplete_bar_rejected_by_default():
    assert "INCOMPLETE_BAR" in validate_bar(make_bar(is_complete=False))


def test_incomplete_bar_allowed_on_provisional_path():
    assert "INCOMPLETE_BAR" not in validate_bar(make_bar(is_complete=False), require_complete=False)


def test_aggregate_rejects_all_incomplete():
    bars = [make_bar(timeframe="5m", start=datetime(2026, 11, 4, 9, 15, tzinfo=IST) + timedelta(minutes=5 * i),
                     is_complete=False) for i in range(3)]
    assert aggregate_5m_to_15m(bars) is None


# --- R4 alignment ---

def test_misaligned_5m_start_detected():
    assert "MISALIGNED_BAR_START" in validate_bar(make_bar(start=datetime(2026, 11, 4, 9, 17, tzinfo=IST)))


def test_before_session_open_detected():
    assert "BEFORE_SESSION_OPEN" in validate_bar(make_bar(start=datetime(2026, 11, 4, 9, 0, tzinfo=IST)))


def test_aggregate_rejects_15m_misaligned_start():
    # three contiguous valid 5m bars but starting at 09:20 (not a 15m boundary)
    bars = make_5m_run(3, start=datetime(2026, 11, 4, 9, 20, tzinfo=IST))
    assert aggregate_5m_to_15m(bars) is None


def test_aggregate_accepts_15m_boundary_start():
    bars = make_5m_run(3, start=datetime(2026, 11, 4, 9, 30, tzinfo=IST))  # 09:30 is a 15m boundary
    assert aggregate_5m_to_15m(bars) is not None


# --- R5 timezone ---

def test_naive_timestamp_detected():
    naive = Bar("SYNTH", "5m", datetime(2026, 11, 4, 9, 15), datetime(2026, 11, 4, 9, 20),
                100, 101, 99, 100.5, 1000)
    assert "NAIVE_TIMESTAMP" in validate_bar(naive)


def test_utc_offset_rejected():
    start = datetime(2026, 11, 4, 3, 45, tzinfo=timezone.utc)  # == 09:15 IST, but offset is +00:00
    bar = Bar("SYNTH", "5m", start, start + timedelta(minutes=5), 100, 101, 99, 100.5, 1000)
    assert "WRONG_TIMEZONE_OFFSET" in validate_bar(bar)


# --- duration / timeframe ---

def test_bad_duration_detected():
    b = Bar("SYNTH", "5m", datetime(2026, 11, 4, 9, 15, tzinfo=IST),
            datetime(2026, 11, 4, 9, 25, tzinfo=IST), 100, 101, 99, 100.5, 1000)
    assert "BAD_BAR_DURATION" in validate_bar(b)


# --- series ordering / dupes ---

def test_series_detects_duplicate():
    bars = make_5m_run(3)
    dup = bars[:1] + bars[:1] + bars[1:]
    assert any(p.startswith("DUPLICATE_BAR_START") for p in validate_series(dup))


# --- aggregation core ---

def test_aggregate_three_contiguous_ok():
    bars = make_5m_run(3)  # starts 09:15 (a 15m boundary)
    agg = aggregate_5m_to_15m(bars)
    assert agg is not None and agg.timeframe == "15m"
    assert agg.open == bars[0].open and agg.close == bars[2].close
    assert agg.high == max(b.high for b in bars) and agg.low == min(b.low for b in bars)
    assert agg.volume == sum(b.volume for b in bars)
    assert "AGGREGATED_FROM_5M" in agg.quality_flags


def test_aggregate_missing_5m_propagates_unavailable():
    bars = make_5m_run(3)
    assert aggregate_5m_to_15m([bars[0], None, bars[2]]) is None


def test_aggregate_requires_exactly_three():
    assert aggregate_5m_to_15m(make_5m_run(2)) is None


# --- R3 optional metadata ---

def test_bad_open_interest_detected():
    assert "BAD_OPEN_INTEREST" in validate_bar(make_bar(open_interest=-5))

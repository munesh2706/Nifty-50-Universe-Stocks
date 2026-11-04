"""Phase A unit tests for canonical bar validation + 5m->15m aggregation.

Synthetic fixtures only; no provider contact.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from gate0.canonical_bars import IST, Bar, aggregate_5m_to_15m, validate_bar, validate_series
from gate0.fixtures.synthetic_bars import make_5m_run, make_bar


def test_valid_bar_has_no_problems():
    assert validate_bar(make_bar()) == []


def test_high_not_max_detected():
    bad = make_bar(o=100, h=100.4, low=99, c=100.5)  # close above high
    assert "HIGH_NOT_MAX" in validate_bar(bad)


def test_low_not_min_detected():
    bad = make_bar(o=100, h=101, low=100.2, c=99.5)  # close below low
    assert "LOW_NOT_MIN" in validate_bar(bad)


def test_non_positive_price_detected():
    bad = make_bar(o=0, h=1, low=0, c=0.5)
    assert "NON_POSITIVE_PRICE" in validate_bar(bad)


def test_negative_volume_detected():
    assert "NEGATIVE_VOLUME" in validate_bar(make_bar(volume=-1))


def test_naive_timestamp_detected():
    naive = Bar("SYNTH", "5m", datetime(2026, 11, 4, 9, 15),
               datetime(2026, 11, 4, 9, 20), 100, 101, 99, 100.5, 1000)
    assert "NAIVE_TIMESTAMP" in validate_bar(naive)


def test_bad_duration_detected():
    b = Bar("SYNTH", "5m", datetime(2026, 11, 4, 9, 15, tzinfo=IST),
            datetime(2026, 11, 4, 9, 25, tzinfo=IST), 100, 101, 99, 100.5, 1000)  # 10 min
    assert "BAD_BAR_DURATION" in validate_bar(b)


def test_series_detects_duplicate_and_out_of_order():
    bars = make_5m_run(3)
    dup = bars[:1] + bars[:1] + bars[1:]  # duplicate first bar_start
    probs = validate_series(dup)
    assert any(p.startswith("DUPLICATE_BAR_START") for p in probs)


def test_series_clean_run_ok():
    assert validate_series(make_5m_run(6)) == []


def test_aggregate_three_contiguous_5m_to_15m():
    bars = make_5m_run(3)
    agg = aggregate_5m_to_15m(bars)
    assert agg is not None
    assert agg.timeframe == "15m"
    assert agg.bar_start_ts == bars[0].bar_start_ts
    assert agg.bar_end_ts == bars[2].bar_end_ts
    assert agg.open == bars[0].open
    assert agg.close == bars[2].close
    assert agg.high == max(b.high for b in bars)
    assert agg.low == min(b.low for b in bars)
    assert agg.volume == sum(b.volume for b in bars)
    assert "AGGREGATED_FROM_5M" in agg.quality_flags


def test_aggregate_missing_5m_propagates_unavailable():
    bars = make_5m_run(3)
    with_hole = [bars[0], None, bars[2]]  # one known-missing 5m bar
    assert aggregate_5m_to_15m(with_hole) is None  # must NOT fabricate


def test_aggregate_noncontiguous_returns_none():
    bars = make_5m_run(3)
    gapped = [bars[0], bars[2], make_5m_run(1, start=bars[2].bar_end_ts + timedelta(minutes=5))[0]]
    assert aggregate_5m_to_15m(gapped) is None


def test_aggregate_requires_exactly_three():
    assert aggregate_5m_to_15m(make_5m_run(2)) is None

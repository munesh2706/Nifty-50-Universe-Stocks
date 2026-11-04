"""Phase A unit tests for gate0.structure (spec v0.2 §7.1-7.3). Synthetic only.

Covers review findings C1-C6.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.structure import (
    AMBIGUOUS_DOUBLE_BREAK,
    BOS_DOWN,
    BOS_UP,
    CHOCH_DOWN,
    Pivot,
    _run_state_machine,
    _segment,
    detect_structure,
)

TICK = 0.05
SRC = "unit-test-tick"
CAL = TradingCalendar(SAMPLE_CALENDAR)
NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)       # Wednesday, regular session
EARLY = datetime(2026, 11, 6, 9, 15, tzinfo=IST)         # early close 13:00 in SAMPLE


def hlc_bars(rows, start=NORMAL, instrument="SYNTH"):
    bars = []
    cur = start
    for h, l, c in rows:
        bars.append(Bar(instrument, "5m", cur, cur + timedelta(minutes=5), c, h, l, c, 1000.0))
        cur += timedelta(minutes=5)
    return bars


def run(bars, buffer_ticks=0):
    return detect_structure(bars, calendar=CAL, tick_size=TICK, tick_size_source=SRC, buffer_ticks=buffer_ticks)


# --- C3: validation / fail-closed ---

def test_empty_input_raises():
    with pytest.raises(ValueError):
        run([])


def test_nan_tick_raises():
    with pytest.raises(ValueError):
        detect_structure(hlc_bars([(20, 10, 15)] * 6), calendar=CAL, tick_size=float("nan"), tick_size_source=SRC)


def test_empty_source_raises():
    with pytest.raises(ValueError):
        detect_structure(hlc_bars([(20, 10, 15)] * 6), calendar=CAL, tick_size=TICK, tick_size_source="  ")


def test_negative_buffer_raises():
    with pytest.raises(ValueError):
        run(hlc_bars([(20, 10, 15)] * 6), buffer_ticks=-1)


def test_off_grid_price_raises():
    with pytest.raises(ValueError):
        run(hlc_bars([(20, 10, 15), (20, 10, 15), (100.03, 10, 15), (20, 10, 15),
                      (20, 10, 15), (20, 10, 15)]))


def test_missing_calendar_raises():
    with pytest.raises(ValueError):
        detect_structure(hlc_bars([(20, 10, 15)] * 6), calendar=None, tick_size=TICK, tick_size_source=SRC)  # type: ignore[arg-type]


def test_unexpected_slot_raises():
    # 13:00 is past the early-close session on 2026-11-06 -> not an expected slot.
    bars = hlc_bars([(20, 10, 15)], start=datetime(2026, 11, 6, 13, 0, tzinfo=IST))
    with pytest.raises(ValueError):
        run(bars)


# --- C1: no repeated BOS (both directions) ---

def test_bullish_bos_not_repeated():
    lows = [10, 10, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
    highs = [20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 31, 31, 31, 31]
    closes = [15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 31, 31, 31, 31]
    res = run(hlc_bars(list(zip(highs, lows, closes))))
    assert sum(1 for e in res.events if e.type == BOS_UP) == 1


def test_bearish_bos_not_repeated():
    rows = [(30, 10, 15), (30, 10, 15), (35, 10, 15), (30, 10, 15), (30, 10, 15), (30, 10, 15),
            (30, 5, 15), (30, 10, 15), (30, 10, 15), (30, 10, 15),
            (30, 4, 4), (30, 4, 4), (30, 4, 4), (30, 4, 4)]
    res = run(hlc_bars(rows))
    assert sum(1 for e in res.events if e.type == BOS_DOWN) == 1


# --- BOS -> CHoCH end to end ---

def test_bullish_bos_then_choch_down():
    lows = [10, 10, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 4]
    highs = [20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 32, 20, 20, 20]
    closes = [15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 32, 15, 15, 5]
    res = run(hlc_bars(list(zip(highs, lows, closes))))
    kinds = [e.type for e in res.events]
    assert BOS_UP in kinds and CHOCH_DOWN in kinds
    bos = next(e for e in res.events if e.type == BOS_UP)
    choch = next(e for e in res.events if e.type == CHOCH_DOWN)
    assert bos.bar_start_ts < choch.bar_start_ts


def test_no_look_ahead_pivots():
    lows = [10, 10, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 4]
    highs = [20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 32, 20, 20, 20]
    closes = [15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 32, 15, 15, 5]
    res = run(hlc_bars(list(zip(highs, lows, closes))))
    for p in res.pivots:
        assert p.confirmation_time > p.pivot_time
    confs = {p.pivot_id: p.confirmation_time for p in res.pivots}
    for e in res.events:
        if e.level_id in confs:
            assert e.bar_start_ts > confs[e.level_id]


# --- C5: ambiguous double-break keeps both level IDs (white-box) ---

def test_ambiguous_double_break_keeps_both_ids():
    t0, tconf = NORMAL, NORMAL + timedelta(minutes=5)
    pivots = [Pivot("high", 10.0, t0, tconf, "H"), Pivot("low", 20.0, t0, tconf, "L")]
    seg = hlc_bars([(25, 5, 15)], start=NORMAL + timedelta(minutes=15))
    events = _run_state_machine(seg, pivots, TICK, 0)
    assert len(events) == 1
    e = events[0]
    assert e.type == AMBIGUOUS_DOUBLE_BREAK
    assert {e.level_id, e.second_level_id} == {"H", "L"}


# --- C2: non-chainable pool grouping + repeatability ---

def _three_price_chain_bars():
    rows = []
    for i in range(11):
        if i == 2:
            rows.append((100.00, 90.0, 95.0))
        elif i == 5:
            rows.append((100.05, 90.0, 95.0))
        elif i == 8:
            rows.append((100.10, 90.0, 95.0))
        else:
            rows.append((99.00, 90.0, 95.0))
    return hlc_bars(rows)


def test_pool_grouping_non_chainable():
    res = run(_three_price_chain_bars())
    high_pools = [p for p in res.pools if p.kind == "high"]
    # 100.00/100.05/100.10 must NOT chain into one 2-tick pool.
    assert len(high_pools) == 1
    assert len(high_pools[0].member_ids) == 2
    assert abs(high_pools[0].reference_price - 100.025) <= TICK


def test_pool_grouping_repeatable():
    a = run(_three_price_chain_bars()).pools
    b = run(_three_price_chain_bars()).pools
    assert [(p.kind, p.reference_price, p.member_ids) for p in a] == \
           [(p.kind, p.reference_price, p.member_ids) for p in b]


# --- C6: equal-high and equal-low pool confirmation boundary ---

def test_equal_high_pool_confirmation_boundary():
    rows = [(50.0, 40.0, 45.0) if i in (2, 8) else (48.0, 40.0, 44.0) for i in range(11)]
    bars = hlc_bars(rows)
    res = run(bars)
    pool = next(p for p in res.pools if p.kind == "high")
    assert len(pool.member_ids) == 2
    # available only after the last member's right-side confirmation (idx8 -> bar idx10 end)
    assert pool.confirmation_time == bars[10].bar_end_ts
    assert pool.confirmation_time > bars[8].bar_start_ts


def test_equal_low_pool_confirmation_boundary():
    rows = [(60.0, 30.0, 45.0) if i in (2, 8) else (60.0, 32.0, 46.0) for i in range(11)]
    bars = hlc_bars(rows)
    res = run(bars)
    pool = next(p for p in res.pools if p.kind == "low")
    assert len(pool.member_ids) == 2
    assert pool.reference_price == 30.0
    assert pool.confirmation_time == bars[10].bar_end_ts


# --- C4: calendar segmentation ---

def test_segment_splits_on_overnight_boundary():
    seg1 = hlc_bars([(20, 10, 15)] * 4, start=NORMAL)
    seg2 = hlc_bars([(20, 10, 15)] * 4, start=EARLY)  # different date (skips holiday 11-05)
    segs = _segment(seg1 + seg2, CAL, "5m")
    assert len(segs) == 2 and len(segs[0]) == 4 and len(segs[1]) == 4


def test_segment_splits_on_missing_slot():
    b = hlc_bars([(20, 10, 15), (20, 10, 15)], start=NORMAL)            # 09:15, 09:20
    b += hlc_bars([(20, 10, 15), (20, 10, 15)],
                  start=NORMAL + timedelta(minutes=15))                  # 09:30, 09:35 (skips 09:25)
    segs = _segment(b, CAL, "5m")
    assert len(segs) == 2


def test_pivot_window_does_not_bridge_gap():
    left = hlc_bars([(20, 10, 15), (20, 10, 15), (30, 10, 15)], start=NORMAL)  # peak idx2, no right bars
    right = hlc_bars([(20, 10, 15), (20, 10, 15)], start=EARLY)
    res = run(left + right)
    assert all(p.price != 30.0 for p in res.pivots)

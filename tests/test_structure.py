"""Phase A unit tests for gate0.structure (spec v0.2 §7.1-7.3). Synthetic only."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.structure import (
    AMBIGUOUS_DOUBLE_BREAK,
    BOS_UP,
    CHOCH_DOWN,
    Pivot,
    _run_state_machine,
    _segment,
    detect_structure,
)

TICK = 0.05
SRC = "unit-test-tick"
START = datetime(2026, 11, 4, 9, 15, tzinfo=IST)


def hlc_bars(rows, start=START, instrument="SYNTH"):
    """Build contiguous aligned 5m bars from (high, low, close) rows; open=close."""
    bars = []
    cur = start
    for h, l, c in rows:
        bars.append(Bar(instrument, "5m", cur, cur + timedelta(minutes=5), c, h, l, c, 1000.0))
        cur += timedelta(minutes=5)
    return bars


# --- validation / fail-closed ---

def test_empty_input_raises():
    with pytest.raises(ValueError):
        detect_structure([], tick_size=TICK, tick_size_source=SRC)


def test_bad_tick_raises():
    with pytest.raises(ValueError):
        detect_structure(hlc_bars([(20, 10, 15)] * 6), tick_size=0, tick_size_source=SRC)


def test_invalid_series_raises():
    bad = hlc_bars([(20, 10, 15)] * 5)
    bad.append(Bar("SYNTH", "5m", bad[-1].bar_end_ts, bad[-1].bar_end_ts + timedelta(minutes=5),
                   5, 1, 2, 10, -1.0))  # negative volume -> invalid
    with pytest.raises(ValueError):
        detect_structure(bad, tick_size=TICK, tick_size_source=SRC)


# --- BOS + CHoCH over one crafted series ---

# idx:      0   1   2   3   4   5   6   7   8   9  10  11  12  13
LOWS = [10, 10, 8, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 4]
HIGHS = [20, 20, 20, 20, 20, 20, 30, 20, 20, 20, 32, 20, 20, 20]
CLOSES = [15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 32, 15, 15, 5]


def _bos_choch_series():
    return hlc_bars(list(zip(HIGHS, LOWS, CLOSES)))


def test_bullish_bos_then_choch_down():
    res = detect_structure(_bos_choch_series(), tick_size=TICK, tick_size_source=SRC)
    types = [(e.type, e.bar_start_ts) for e in res.events]
    kinds = [t for t, _ in types]
    assert BOS_UP in kinds
    assert CHOCH_DOWN in kinds
    bos_ts = next(ts for t, ts in types if t == BOS_UP)
    choch_ts = next(ts for t, ts in types if t == CHOCH_DOWN)
    assert bos_ts == START + timedelta(minutes=5 * 10)   # idx10
    assert choch_ts == START + timedelta(minutes=5 * 13)  # idx13
    assert bos_ts < choch_ts


def test_no_premature_bos_before_confirmation():
    res = detect_structure(_bos_choch_series(), tick_size=TICK, tick_size_source=SRC)
    # No structure event may occur before the swing-high at idx6 is confirmed (idx8 end).
    first = min(e.bar_start_ts for e in res.events)
    assert first >= START + timedelta(minutes=5 * 10)


def test_no_look_ahead_pivots():
    res = detect_structure(_bos_choch_series(), tick_size=TICK, tick_size_source=SRC)
    for p in res.pivots:
        assert p.confirmation_time > p.pivot_time
    # every BOS event fires strictly after the broken pivot's confirmation
    confs = {p.pivot_id: p.confirmation_time for p in res.pivots}
    for e in res.events:
        if e.level_id in confs:
            assert e.bar_start_ts > confs[e.level_id]


# --- degenerate double break (white-box; naturally near-impossible) ---

def test_ambiguous_double_break_stays_neutral():
    t0 = START
    tconf = START + timedelta(minutes=5)
    # swing low price (20) ABOVE swing high price (10): overlap band.
    pivots = [
        Pivot("high", 10.0, t0, tconf, "H"),
        Pivot("low", 20.0, t0, tconf, "L"),
    ]
    seg = hlc_bars([(25, 5, 15)], start=START + timedelta(minutes=15))  # close 15 is between 10 and 20
    events = _run_state_machine(seg, pivots, TICK, 0)
    assert [e.type for e in events] == [AMBIGUOUS_DOUBLE_BREAK]


# --- equal-extreme pools ---

def test_equal_high_pool_detected():
    # two equal highs at 50.00 (idx2, idx8), neighbors lower -> one high pool.
    rows = []
    for i in range(11):
        if i in (2, 8):
            rows.append((50.0, 40.0, 45.0))
        else:
            rows.append((48.0, 40.0, 44.0))
    res = detect_structure(hlc_bars(rows), tick_size=TICK, tick_size_source=SRC)
    high_pools = [p for p in res.pools if p.kind == "high"]
    assert len(high_pools) == 1
    pool = high_pools[0]
    assert pool.reference_price == 50.0
    assert len(pool.member_ids) == 2
    assert pool.tick_size == TICK and pool.tick_size_source == SRC
    # available only after the last member confirms
    assert pool.confirmation_time > START


# --- segmentation ---

def test_segment_splits_on_gap():
    seg1 = hlc_bars([(20, 10, 15)] * 4, start=START)
    # overnight gap: next day 09:15
    seg2 = hlc_bars([(20, 10, 15)] * 4, start=datetime(2026, 11, 6, 9, 15, tzinfo=IST))
    segs = _segment(seg1 + seg2)
    assert len(segs) == 2
    assert len(segs[0]) == 4 and len(segs[1]) == 4


def test_pivot_window_does_not_bridge_gap():
    # A "swing high" peak whose confirmation bars fall on the other side of a gap
    # must NOT be detected (window cannot bridge the segment boundary).
    left = hlc_bars([(20, 10, 15), (20, 10, 15), (30, 10, 15)], start=START)  # peak at idx2, no right bars
    right = hlc_bars([(20, 10, 15), (20, 10, 15)],
                     start=datetime(2026, 11, 6, 9, 15, tzinfo=IST))
    res = detect_structure(left + right, tick_size=TICK, tick_size_source=SRC)
    assert all(p.price != 30.0 for p in res.pivots)  # peak never confirmed across the gap

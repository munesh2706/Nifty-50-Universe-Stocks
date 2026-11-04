"""Phase A unit tests for gate0.displacement (spec v0.2 §7.4). Synthetic only.

Covers ChatGPT scope-agreement 029 amendments 1-6.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.displacement import _atr_series, detect_displacement
from gate0.structure import BOS_DOWN, BOS_UP, Pivot, StructureEvent, StructureResult

TICK = 0.05
SRC = "unit-test-tick"
CAL = TradingCalendar(SAMPLE_CALENDAR)
NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
EARLY = datetime(2026, 11, 6, 9, 15, tzinfo=IST)

# 14 warm-up bars with TR == 0.10 each -> seeded ATR(14) == 0.10 at index 13.
WARMUP = [(100.05, 100.10, 100.00, 100.05)] * 14  # (open, high, low, close)


def build(specs, start=NORMAL, instrument="SYNTH"):
    bars = []
    cur = start
    for o, h, l, c in specs:
        bars.append(Bar(instrument, "5m", cur, cur + timedelta(minutes=5), o, h, l, c, 1000.0))
        cur += timedelta(minutes=5)
    return bars


def structure_for(bar, direction, level, instrument="SYNTH", level_id=None):
    lid = level_id or f"{instrument}:{NORMAL.isoformat()}:{'H' if direction == 'up' else 'L'}"
    piv = Pivot("high" if direction == "up" else "low", level, NORMAL, NORMAL, lid)
    ev = StructureEvent(BOS_UP if direction == "up" else BOS_DOWN, bar.bar_start_ts, direction, level, lid)
    return StructureResult(events=[ev], pivots=[piv], pools=[])


def run(bars, structure, **kw):
    return detect_displacement(bars, structure, calendar=CAL, tick_size=TICK, tick_size_source=SRC, **kw)


# --- amendment 1: ATR seed + Wilder update (hand-checked) ---

def test_atr_seed_and_wilder_update():
    seg = build(WARMUP + [(100.00, 100.25, 100.00, 100.10)])  # 15th TR = 0.25
    atr = _atr_series(seg)
    # Decimal, exact: 14 TRs of 0.10 -> seed exactly 0.10
    assert atr[13] == Decimal("0.10")
    assert isinstance(atr[13], Decimal)
    assert atr[14] == (Decimal("0.10") * 13 + Decimal("0.25")) / Decimal(14)


def test_d2_tr_and_atr_exact_decimal():
    # non-round-looking price difference 100.10-100.00 is exactly Decimal('0.10')
    # through TR seed and Wilder update (not a rounded binary float like 0.1).
    seg = build(WARMUP + [(100.00, 100.10, 100.00, 100.10)])
    atr = _atr_series(seg)
    assert atr[13] == Decimal("0.10")
    assert atr[14] == Decimal("0.10")  # another 0.10 TR keeps it exact


# --- bullish / bearish single-candle qualification ---

def test_bullish_single_candle_qualifies_and_atr_excludes_self():
    disp = (100.00, 101.00, 100.00, 101.00)  # net body 1.00 up, huge self-range
    bars = build(WARMUP + [disp])
    s = structure_for(bars[14], "up", 100.50)
    res = run(bars, s)
    assert len(res) == 1
    d = res[0]
    assert d.direction == "up" and len(d.bar_ids) == 1
    assert d.net_body == pytest.approx(1.00)
    assert d.atr_value == pytest.approx(0.10)  # ATR excludes the displacement bar itself
    assert d.volume_flag is None


def test_bearish_single_candle_qualifies():
    disp = (100.00, 100.00, 99.00, 99.00)  # net body 1.00 down
    bars = build(WARMUP + [disp])
    s = structure_for(bars[14], "down", 99.50)
    res = run(bars, s)
    assert len(res) == 1 and res[0].direction == "down"


# --- threshold equality / below / above ---

def test_threshold_exact_qualifies():
    bars = build(WARMUP + [(100.00, 100.10, 100.00, 100.10)])  # body 0.10 == threshold 0.10
    res = run(bars, structure_for(bars[14], "up", 100.05))
    assert len(res) == 1


def test_threshold_just_below_rejects():
    bars = build(WARMUP + [(100.00, 100.05, 100.00, 100.05)])  # body 0.05 < 0.10
    res = run(bars, structure_for(bars[14], "up", 100.00))
    assert res == []


def test_threshold_just_above_qualifies():
    bars = build(WARMUP + [(100.00, 100.15, 100.00, 100.15)])  # body 0.15 >= 0.10
    res = run(bars, structure_for(bars[14], "up", 100.05))
    assert len(res) == 1


# --- amendment 2: multi-candle + shortest selection + doji breaks + one per BOS ---

def test_multicandle_shortest_qualifying_selected():
    d1 = (100.00, 100.10, 100.00, 100.10)  # body 0.10 up
    d2 = (100.10, 100.15, 100.10, 100.15)  # body 0.05 up (alone < 0.10)
    bars = build(WARMUP + [d1, d2])
    res = run(bars, structure_for(bars[15], "up", 100.05))
    assert len(res) == 1                 # one per BOS
    assert len(res[0].bar_ids) == 2      # L=1 rejected, L=2 chosen


def test_doji_breaks_sequence():
    d1 = (100.00, 100.10, 100.00, 100.10)
    doji = (100.10, 100.15, 100.05, 100.10)  # open == close -> not positive body
    bars = build(WARMUP + [d1, doji])
    res = run(bars, structure_for(bars[15], "up", 100.05))
    assert res == []


# --- amendment 1: warm-up gating ---

def test_no_evaluation_before_14_prior_trs():
    bars = build(WARMUP[:13] + [(100.00, 101.00, 100.00, 101.00)])  # e=13 -> only 13 prior TRs
    res = run(bars, structure_for(bars[13], "up", 100.50))
    assert res == []


# --- amendment 1/6: segment reset (no bridge across session boundary) ---

def test_atr_resets_per_segment():
    seg1 = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)], start=NORMAL)
    seg2 = build([(100.00, 100.10, 100.00, 100.05), (100.00, 101.00, 100.00, 101.00)], start=EARLY)
    bars = seg1 + seg2
    s = structure_for(seg2[1], "up", 100.50)  # BOS early in seg2 -> insufficient warm-up
    assert run(bars, s) == []


# --- amendment 4: linkage / direction / level validation ---

def test_wrong_level_not_beyond_rejects():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = structure_for(bars[14], "up", 101.50)  # close 101 not > 101.50
    assert run(bars, s) == []


def test_unresolved_pivot_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    ev = StructureEvent(BOS_UP, bars[14].bar_start_ts, "up", 100.5, "SYNTH:nope:H")
    with pytest.raises(ValueError):
        run(bars, StructureResult(events=[ev], pivots=[], pools=[]))


def test_mismatched_instrument_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    lid = "OTHER:x:H"
    ev = StructureEvent(BOS_UP, bars[14].bar_start_ts, "up", 100.5, lid)
    piv = Pivot("high", 100.5, NORMAL, NORMAL, lid)
    with pytest.raises(ValueError):
        run(bars, StructureResult(events=[ev], pivots=[piv], pools=[]))


def test_duplicate_bos_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    lid = f"SYNTH:{NORMAL.isoformat()}:H"
    ev = StructureEvent(BOS_UP, bars[14].bar_start_ts, "up", 100.5, lid)
    piv = Pivot("high", 100.5, NORMAL, NORMAL, lid)
    with pytest.raises(ValueError):
        run(bars, StructureResult(events=[ev, ev], pivots=[piv], pools=[]))


# --- amendment 6: fail-closed config / input ---

def test_empty_input_raises():
    with pytest.raises(ValueError):
        run([], StructureResult())


def test_bad_mult_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    with pytest.raises(ValueError):
        run(bars, structure_for(bars[14], "up", 100.5), displacement_atr_mult=0)


def test_bad_sequence_max_len_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    with pytest.raises(ValueError):
        run(bars, structure_for(bars[14], "up", 100.5), sequence_max_len=0)
    with pytest.raises(ValueError):
        run(bars, structure_for(bars[14], "up", 100.5), sequence_max_len=999)


def test_off_grid_price_raises():
    bars = build(WARMUP + [(100.00, 100.03, 100.00, 100.03)])
    with pytest.raises(ValueError):
        run(bars, structure_for(bars[14], "up", 100.0))


# --- determinism ---

def test_deterministic_repeatable():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = structure_for(bars[14], "up", 100.50)
    a, b = run(bars, s), run(bars, s)
    assert [d.displacement_id for d in a] == [d.displacement_id for d in b]
    assert a[0].displacement_id == b[0].displacement_id


# ----- D1: BOS/pivot coherence & confirmation-timing -----

def _struct(bar, type_, direction, level, kind, conf, price, level_id="SYNTH:p:X"):
    piv = Pivot(kind, price, NORMAL, conf, level_id)
    ev = StructureEvent(type_, bar.bar_start_ts, direction, level, level_id)
    return StructureResult(events=[ev], pivots=[piv], pools=[])


def test_d1_bos_up_with_low_pivot_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "up", 100.50, "low", NORMAL, 100.50)  # wrong pivot kind
    with pytest.raises(ValueError):
        run(bars, s)


def test_d1_type_direction_mismatch_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "down", 100.50, "high", NORMAL, 100.50)
    with pytest.raises(ValueError):
        run(bars, s)


def test_d1_pivot_not_confirmed_before_bos_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "up", 100.50, "high", bars[14].bar_start_ts, 100.50)  # conf == BOS bar
    with pytest.raises(ValueError):
        run(bars, s)


def test_d1_level_price_mismatch_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "up", 100.50, "high", NORMAL, 100.55)  # level != pivot price
    with pytest.raises(ValueError):
        run(bars, s)


def test_d1_off_tick_level_raises():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "up", 100.53, "high", NORMAL, 100.53)  # off-grid price
    with pytest.raises(ValueError):
        run(bars, s)


def test_d1_valid_timing_qualifies():
    bars = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)])
    s = _struct(bars[14], BOS_UP, "up", 100.50, "high", NORMAL, 100.50)  # confirmed well before
    assert len(run(bars, s)) == 1


# ----- D2: deterministic decimal threshold (guards binary FP, e.g. 0.7*0.1) -----

def test_d2_nonround_mult_exact_equality_qualifies():
    # threshold = 1.5 * 0.10 = 0.15; net body 0.15 must qualify under exact decimal
    # comparison (naive binary float 1.5*0.1 == 0.15000000000000002 would wrongly reject).
    bars = build(WARMUP + [(100.00, 100.15, 100.00, 100.15)])
    s = structure_for(bars[14], "up", 100.05)
    assert len(run(bars, s, displacement_atr_mult=1.5)) == 1


def test_d2_just_below_rejects():
    bars = build(WARMUP + [(100.00, 100.10, 100.00, 100.10)])  # body 0.10 < 0.15
    s = structure_for(bars[14], "up", 100.05)
    assert run(bars, s, displacement_atr_mult=1.5) == []


# ----- D3: extra coverage -----

def test_d3_missing_slot_resets_atr():
    seg_a = build(WARMUP, start=NORMAL)                                   # 14 bars 09:15..
    disp = build([(100.00, 101.00, 100.00, 101.00)],
                 start=NORMAL + timedelta(minutes=5 * 15))                # skip one slot -> new segment
    bars = seg_a + disp
    s = structure_for(disp[0], "up", 100.50)  # BOS is first bar of a fresh segment -> no warm-up
    assert run(bars, s) == []


def test_d3_bearish_multicandle():
    d1 = (100.00, 100.00, 99.90, 99.90)   # body 0.10 down
    d2 = (99.90, 99.90, 99.85, 99.85)     # body 0.05 down (alone < 0.10)
    bars = build(WARMUP + [d1, d2])
    res = run(bars, structure_for(bars[15], "down", 99.95))
    assert len(res) == 1 and res[0].direction == "down" and len(res[0].bar_ids) == 2


def test_d3_opposite_candle_interrupts():
    d1 = (100.00, 100.10, 100.00, 100.10)       # up
    opp = (100.10, 100.15, 99.90, 100.00)       # open==close? no: open 100.10, close 100.00 -> down
    bars = build(WARMUP + [d1, opp])
    # level 99.95 is below the final close (100.00) so the BOS-close condition PASSES;
    # the only reason no displacement is emitted is the opposite-body interruption.
    assert run(bars, structure_for(bars[15], "up", 99.95)) == []


def test_d3_post_gap_requires_14_new_trs():
    seg_a = build(WARMUP, start=NORMAL)                                   # ends 10:25
    gap_start = NORMAL + timedelta(minutes=5 * 15)                        # 10:30 (skips 10:25 slot)
    # 13 prior TRs after the gap -> still ineligible
    segb_bad = build(WARMUP[:13] + [(100.00, 101.00, 100.00, 101.00)], start=gap_start)
    assert run(seg_a + segb_bad, structure_for(segb_bad[13], "up", 100.50)) == []
    # 14 prior TRs after the gap -> eligible
    segb_ok = build(WARMUP + [(100.00, 101.00, 100.00, 101.00)], start=gap_start)
    assert len(run(seg_a + segb_ok, structure_for(segb_ok[14], "up", 100.50))) == 1

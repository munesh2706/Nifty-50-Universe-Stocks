"""Phase A unit tests for gate0.ranking (Stage 1 weighted score, spec v0.3 §4).
Synthetic only.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.structure import BOS_UP, BOS_DOWN, StructureEvent, StructureResult
from gate0.ranking import (
    build_shortlist,
    resolve_neutral_band,
    rs_score,
    score_symbol,
    structure_score,
    trend_score,
)

START = datetime(2026, 11, 4, 9, 15, tzinfo=IST)


def make_bars15(closes, volumes=None, start=START, instrument="SYNTH"):
    bars = []
    cur = start
    volumes = volumes or [1000.0] * len(closes)
    for c, v in zip(closes, volumes):
        bars.append(Bar(instrument, "15m", cur, cur + timedelta(minutes=15), c, c + 1, c - 1, c, v))
        cur += timedelta(minutes=15)
    return bars


# --- rs_score ---

def test_rs_score_all_intervals_agree():
    stock = [100, 101, 102, 104, 108, 112]  # rising fast
    nifty = [100, 100, 100, 100, 100, 100]  # flat
    score, intervals = rs_score(stock, nifty, index=5, direction="up")
    assert score == 30
    assert len(intervals) == 3


def test_rs_score_disagreement_zero():
    stock = [100, 99, 98, 97, 96, 95]  # falling
    nifty = [100, 100, 100, 100, 100, 100]
    score, _ = rs_score(stock, nifty, index=5, direction="up")
    assert score == 0


def test_rs_score_below_threshold_zero():
    stock = [100.00, 100.001, 100.002, 100.003, 100.004, 100.005]
    nifty = [100.00, 100.000, 100.000, 100.000, 100.000, 100.000]
    score, _ = rs_score(stock, nifty, index=5, direction="up", threshold_pct=Decimal("0.15"))
    assert score == 0


def test_rs_score_invalid_direction_raises():
    with pytest.raises(ValueError):
        rs_score([1, 2], [1, 2], index=1, direction="sideways")


# --- trend_score ---

def test_trend_score_bullish_alignment():
    # 25 rising closes -> EMA9 > EMA21, price above VWAP, accelerating late
    closes = [100 + i * 0.5 for i in range(25)]
    bars = make_bars15(closes)
    total, trend_sub, momentum_sub = trend_score(bars, index=24, direction="up")
    assert trend_sub == 15
    assert momentum_sub in (8, 15)
    assert total == trend_sub + momentum_sub


def test_trend_score_not_warm_enough_zero():
    closes = [100.0] * 5
    bars = make_bars15(closes)
    total, trend_sub, momentum_sub = trend_score(bars, index=4, direction="up")
    assert trend_sub == 0  # EMA21 not warm yet


def test_momentum_accelerating_vs_decelerating():
    # accelerating: last 3-bar move bigger than prior 3-bar move
    closes_accel = [100, 100, 100, 100, 100.1, 100.3, 100.8]
    bars = make_bars15(closes_accel)
    _, _, m = trend_score(bars, index=6, direction="up")
    assert m == 15

    # prior move (idx0->3) = 1.5, recent move (idx3->6) = 0.18 -> decelerating
    closes_decel = [100, 100.5, 101.0, 101.5, 101.6, 101.65, 101.68]
    bars2 = make_bars15(closes_decel)
    _, _, m2 = trend_score(bars2, index=6, direction="up")
    assert m2 == 8


# --- structure_score ---

def test_structure_score_state_agrees_and_recent_bos():
    bars = make_bars15([100] * 10)
    bos_ts = bars[7].bar_start_ts  # 2 bars before the as-of bar (index 9)
    ev = StructureEvent(BOS_UP, bos_ts, "up", 100.0, "SYNTH:x:H")
    structure = StructureResult(events=[ev], pivots=[], pools=[])
    total, state_sub, recency_sub = structure_score(structure, bars, index=9, direction="up")
    assert state_sub == 15
    assert recency_sub == 15  # within last 3 bars
    assert total == 30


def test_structure_score_disagreement_zeroes_both_subs():
    bars = make_bars15([100] * 10)
    ev = StructureEvent(BOS_DOWN, bars[7].bar_start_ts, "down", 100.0, "SYNTH:x:L")
    structure = StructureResult(events=[ev], pivots=[], pools=[])
    total, state_sub, recency_sub = structure_score(structure, bars, index=9, direction="up")
    assert state_sub == 0
    assert recency_sub == 0
    assert total == 0


def test_structure_score_no_events_neutral():
    bars = make_bars15([100] * 5)
    structure = StructureResult(events=[], pivots=[], pools=[])
    total, state_sub, recency_sub = structure_score(structure, bars, index=4, direction="up")
    assert total == 0


def test_structure_score_old_bos_recency_zero():
    bars = make_bars15([100] * 15)
    ev = StructureEvent(BOS_UP, bars[0].bar_start_ts, "up", 100.0, "SYNTH:x:H")
    structure = StructureResult(events=[ev], pivots=[], pools=[])
    total, state_sub, recency_sub = structure_score(structure, bars, index=14, direction="up")
    assert state_sub == 15  # state still BULL (last BOS was up)
    assert recency_sub == 0  # but it's 14 bars back, outside the 10-bar window


# --- score_symbol (missing data / UNAVAILABLE) ---

def test_score_symbol_none_on_invalid_series():
    # canonical_bars.validate_series does not itself detect timestamp gaps
    # (that is a separate calendar/segmentation concern, by design); use an
    # actually-invalid bar (negative volume) to trigger fail-closed exclusion.
    good = make_bars15([100] * 10, volumes=[1000.0] * 10)
    bad_bar = Bar(good[5].instrument_id, good[5].timeframe, good[5].bar_start_ts,
                  good[5].bar_end_ts, 100, 101, 99, 100, -5.0)  # negative volume
    bad = good[:5] + [bad_bar] + good[6:]
    nifty = make_bars15([100] * 10)
    structure = StructureResult(events=[], pivots=[], pools=[])
    result = score_symbol("BADSTOCK", "up", stock_bars_15m=bad, nifty_bars_15m=nifty,
                          structure=structure, index=8)
    assert result is None


def test_score_symbol_none_when_not_warm():
    bars = make_bars15([100] * 5)
    nifty = make_bars15([100] * 5)
    structure = StructureResult(events=[], pivots=[], pools=[])
    result = score_symbol("X", "up", stock_bars_15m=bars, nifty_bars_15m=nifty,
                          structure=structure, index=4)
    assert result is None


def test_score_symbol_eligible_strong_bullish():
    closes = [100 + i * 0.6 for i in range(25)]
    stock = make_bars15(closes)
    nifty = make_bars15([100.0] * 25)
    ev = StructureEvent(BOS_UP, stock[22].bar_start_ts, "up", 100.0, "SYNTH:x:H")
    structure = StructureResult(events=[ev], pivots=[], pools=[])
    result = score_symbol("GOODSTOCK", "up", stock_bars_15m=stock, nifty_bars_15m=nifty,
                          structure=structure, index=24)
    assert result is not None
    assert result.eligible
    assert result.detail.total > 45


# --- resolve_neutral_band (the corrected logic) ---

def _fake_score(total: int) -> "object":
    from gate0.ranking import DimensionDetail, SymbolScore
    detail = DimensionDetail(total, (), 0, 0, 0, 0, 0, 0, "unavailable", total)
    return SymbolScore("X", "up", detail, eligible=total >= 45)


def test_neutral_band_only_bull_qualifies():
    bull = _fake_score(60)
    bear = _fake_score(30)  # below floor
    bull_in, bear_in = resolve_neutral_band(bull, bear, band=5)
    assert bull_in and not bear_in


def test_neutral_band_similar_scores_ambiguous():
    bull = _fake_score(50)
    bear = _fake_score(52)  # both qualify, diff=2 < band
    bull_in, bear_in = resolve_neutral_band(bull, bear, band=5)
    assert not bull_in and not bear_in


def test_neutral_band_clear_difference_assigns_stronger_only():
    bull = _fake_score(70)
    bear = _fake_score(50)  # both qualify, diff=20 >= band
    bull_in, bear_in = resolve_neutral_band(bull, bear, band=5)
    assert bull_in and not bear_in


def test_neutral_band_neither_qualifies():
    bull = _fake_score(20)
    bear = _fake_score(10)
    bull_in, bear_in = resolve_neutral_band(bull, bear, band=5)
    assert not bull_in and not bear_in


# --- build_shortlist (never pad, correct ranking order) ---

def test_shortlist_never_pads_below_five():
    s1 = _fake_score(60)
    scores = [(s1, None)]
    sl = build_shortlist(scores, max_per_side=5)
    assert len(sl.bullish) == 1
    assert len(sl.bearish) == 0


def test_shortlist_caps_at_max_and_ranks_descending():
    scores = [(_fake_score(10 * i), None) for i in range(1, 8)]  # 7 candidates
    sl = build_shortlist(scores, max_per_side=5)
    assert len(sl.bullish) == 5
    totals = [s.detail.total for s in sl.bullish]
    assert totals == sorted(totals, reverse=True)
    assert totals[0] == 70  # the strongest of the 7

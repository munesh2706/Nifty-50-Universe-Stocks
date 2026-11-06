"""Phase A unit tests for gate0.scan (universe-scan orchestration, spec
v0.3 §4-§6). Synthetic only. The "golden path" fixture below was built and
verified interactively (real BOS -> real qualifying displacement -> real
confirmed zone -> real resolved target -> eligible Stage 2 candidate) before
being transcribed here, exactly as the other Phase A modules' fixtures are."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.scan import (
    COVERAGE_BELOW_THRESHOLD,
    DATA_UNAVAILABLE,
    STALE_LATEST_BAR,
    STATUS_NO_TRADE,
    STATUS_PARTIAL,
    STATUS_UNIVERSE_WIDE,
    ScanConfig,
    SymbolBars,
    resolve_target_price,
    run_universe_scan,
)
from gate0.structure import Pivot, StructureResult

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
CAL = TradingCalendar(SAMPLE_CALENDAR)


def bar5(o, h, l, c, start, instrument="SYNTH"):
    return Bar(instrument, "5m", start, start + timedelta(minutes=5), o, h, l, c, 1000.0)


def bars15(closes, start=NORMAL, instrument="SYNTH"):
    out, cur = [], start
    for c in closes:
        out.append(Bar(instrument, "15m", cur, cur + timedelta(minutes=15), c, c + 1, c - 1, c, 1000.0))
        cur += timedelta(minutes=15)
    return out


def strong_bullish_5m_bars():
    """14-bar ATR warmup, a real swing-high BOS_UP confirmed at 11:15, a
    qualifying single-bar displacement on that same bar, a touch then a
    confirmation close beyond the Approach-B zone's proximal (31), and a
    later confirmed swing high (55) that resolve_target_price can use."""
    cur = NORMAL
    bars = []
    for _ in range(14):
        bars.append(bar5(14.5, 15, 14, 14.5, cur)); cur += timedelta(minutes=5)
    for h, l, c in [(20, 10, 15), (20, 10, 15), (20, 8, 15), (20, 10, 15), (20, 10, 15),
                     (20, 10, 15), (30, 10, 15), (20, 10, 15), (20, 10, 15), (20, 10, 15)]:
        bars.append(bar5(c, h, l, c, cur)); cur += timedelta(minutes=5)
    bars.append(bar5(15, 31, 15, 31, cur)); cur += timedelta(minutes=5)       # D1/final: BOS_UP confirm + displacement
    bars.append(bar5(31, 32, 20, 25, cur)); cur += timedelta(minutes=5)       # touch (dips into [15,31])
    bars.append(bar5(25, 36, 24, 35, cur)); cur += timedelta(minutes=5)       # confirm (closes beyond 31)
    for o, h, l, c in [(35, 36, 34, 35), (35, 36, 34, 35), (35, 56, 34, 55),
                       (35, 36, 34, 35), (35, 36, 34, 35)]:
        bars.append(bar5(o, h, l, c, cur)); cur += timedelta(minutes=5)       # confirmed swing high (55) for the target
    bars.append(bar5(35, 36, 34, 36, cur)); cur += timedelta(minutes=5)      # current price (36), below the target
    return bars


def strong_bullish_symbol(symbol="GOODSTOCK"):
    closes15 = [100 + i * 0.6 for i in range(25)]
    return SymbolBars(symbol=symbol, bars_15m=bars15(closes15), bars_5m=strong_bullish_5m_bars(),
                      volume_baseline=1000.0)


def flat_nifty_15m(n=25):
    return bars15([100.0] * n, instrument="NIFTY50")


def neutral_symbol(symbol="FLATSTOCK"):
    bars = [bar5(100.0, 100.5, 99.5, 100.0, NORMAL + timedelta(minutes=5 * i)) for i in range(40)]
    closes15 = [100.0] * 25
    return SymbolBars(symbol=symbol, bars_15m=bars15(closes15), bars_5m=bars, volume_baseline=1000.0)


def invalid_symbol(symbol="BADSTOCK"):
    bars = neutral_symbol(symbol).bars_5m
    bad = Bar(symbol, "5m", bars[5].bar_start_ts, bars[5].bar_end_ts, 100, 101, 99, 100, -5.0)
    bars5 = bars[:5] + [bad] + bars[6:]
    return SymbolBars(symbol=symbol, bars_15m=neutral_symbol(symbol).bars_15m, bars_5m=bars5)


# --- golden path: a real eligible Stage 2 candidate reaches UNIVERSE_WIDE ---

def test_golden_path_bullish_candidate_reaches_universe_wide():
    sb = strong_bullish_symbol()
    config = ScanConfig(coverage_threshold=1, approach="B", boundary_type="full_range")
    result = run_universe_scan([sb], flat_nifty_15m(), calendar=CAL, config=config)
    assert result.healthy_count == 1
    assert "GOODSTOCK" in [s.symbol for s in result.stage1_shortlist.bullish]
    assert result.bullish.status == STATUS_UNIVERSE_WIDE
    assert len(result.bullish.candidates) == 1
    assert result.bullish.candidates[0].symbol == "GOODSTOCK"
    assert result.bullish.candidates[0].net_rr >= 1.5


def test_golden_path_bearish_side_independently_no_trade():
    # The same bullish-only universe has nothing on the bearish side --
    # NO_TRADE for "down", independent of bullish's UNIVERSE_WIDE result.
    sb = strong_bullish_symbol()
    config = ScanConfig(coverage_threshold=1)
    result = run_universe_scan([sb], flat_nifty_15m(), calendar=CAL, config=config)
    assert result.bearish.status == STATUS_NO_TRADE
    assert result.bearish.candidates == ()


# --- per-symbol DATA_UNAVAILABLE never blocks the rest of the universe ---

def test_bad_symbol_marked_unavailable_others_still_scanned():
    good = strong_bullish_symbol()
    bad = invalid_symbol()
    config = ScanConfig(coverage_threshold=1)
    result = run_universe_scan([good, bad], flat_nifty_15m(), calendar=CAL, config=config)
    assert result.total == 2
    assert result.healthy_count == 1
    bad_health = next(h for h in result.health if h.symbol == "BADSTOCK")
    assert not bad_health.healthy
    assert DATA_UNAVAILABLE in bad_health.reason_codes
    assert result.bullish.status == STATUS_UNIVERSE_WIDE  # unaffected by BADSTOCK


# --- review 050: a symbol stale relative to the universe's own clock ---

def test_symbol_missing_only_its_latest_bar_is_stale_not_silently_ranked():
    # Nifty (and the rest of the universe) has data through the latest 15m
    # bar; this symbol's OWN latest supplied bar is one slot older (its most
    # recent candle is simply missing) -- every per-bar field is otherwise
    # valid, so validate_series alone would not catch it. It must be marked
    # DATA_UNAVAILABLE (STALE_LATEST_BAR), never ranked "as of" its own
    # older bar while the rest of the universe is judged as of now.
    good = strong_bullish_symbol()
    nifty = flat_nifty_15m()
    stale = SymbolBars(symbol="STALESTOCK", bars_15m=good.bars_15m[:-1],  # drop only the latest bar
                       bars_5m=good.bars_5m, volume_baseline=1000.0)
    config = ScanConfig(coverage_threshold=1)
    result = run_universe_scan([good, stale], nifty, calendar=CAL, config=config)
    stale_health = next(h for h in result.health if h.symbol == "STALESTOCK")
    assert not stale_health.healthy
    assert STALE_LATEST_BAR in stale_health.reason_codes
    assert "STALESTOCK" not in [s.symbol for s in result.stage1_shortlist.bullish]
    assert result.bullish.status == STATUS_UNIVERSE_WIDE  # GOODSTOCK is unaffected


def test_symbol_matching_universe_latest_bar_is_still_scored_normally():
    good = strong_bullish_symbol()
    nifty = flat_nifty_15m()
    config = ScanConfig(coverage_threshold=1)
    result = run_universe_scan([good], nifty, calendar=CAL, config=config)
    good_health = next(h for h in result.health if h.symbol == "GOODSTOCK")
    assert good_health.healthy
    assert good_health.reason_codes == ()


# --- coverage threshold: PARTIAL vs NO_TRADE are never conflated ---

def test_below_coverage_threshold_is_partial_even_with_a_candidate():
    sb = strong_bullish_symbol()
    config = ScanConfig(coverage_threshold=10)  # only 1/10 healthy -> below threshold
    result = run_universe_scan([sb], flat_nifty_15m(), calendar=CAL, config=config)
    assert result.healthy_count == 1
    assert result.bullish.status == STATUS_PARTIAL
    assert COVERAGE_BELOW_THRESHOLD in result.bullish.reason_codes
    assert len(result.bullish.candidates) == 1  # still shown among available symbols, per §6


def test_no_trade_when_coverage_sufficient_but_nothing_qualifies():
    flat = neutral_symbol()
    config = ScanConfig(coverage_threshold=1)
    result = run_universe_scan([flat], flat_nifty_15m(), calendar=CAL, config=config)
    assert result.healthy_count == 1
    assert result.bullish.status == STATUS_NO_TRADE
    assert result.bearish.status == STATUS_NO_TRADE


def test_never_pads_final_candidates_beyond_two_per_direction():
    symbols = [strong_bullish_symbol(f"GOOD{i}") for i in range(3)]
    config = ScanConfig(coverage_threshold=1, max_final_candidates=2)
    result = run_universe_scan(symbols, flat_nifty_15m(), calendar=CAL, config=config)
    assert len(result.bullish.candidates) <= 2


# --- resolve_target_price ---

def test_resolve_target_price_up_picks_nearest_confirmed_high_above_price():
    structure = StructureResult(
        pivots=[Pivot("high", 110.0, NORMAL, NORMAL + timedelta(minutes=10), "p1"),
                Pivot("high", 120.0, NORMAL, NORMAL + timedelta(minutes=10), "p2")],
    )
    assert resolve_target_price(structure, "up", current_price=105.0) == 110.0


def test_resolve_target_price_down_picks_nearest_confirmed_low_below_price():
    structure = StructureResult(
        pivots=[Pivot("low", 90.0, NORMAL, NORMAL + timedelta(minutes=10), "p1"),
                Pivot("low", 80.0, NORMAL, NORMAL + timedelta(minutes=10), "p2")],
    )
    assert resolve_target_price(structure, "down", current_price=95.0) == 90.0


def test_resolve_target_price_none_when_no_objective_level_exists():
    structure = StructureResult(pivots=[Pivot("high", 100.0, NORMAL, NORMAL + timedelta(minutes=10), "p1")])
    assert resolve_target_price(structure, "up", current_price=105.0) is None  # the only high is BELOW price

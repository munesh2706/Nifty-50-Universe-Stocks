"""Stage 1 directional ranking (15m) — Gate 0 harness, Phase A.

Implements spec v0.3 §4 in full: the three mandatory scored dimensions
(relative strength, trend+momentum, market structure — 0-30 each, 90 total),
the optional volume tiebreak modifier (§4.2), missing-data exclusion (§4.3),
the qualifying floor + corrected neutral-band resolution (§4.4), and the
Stage 1 shortlist (§4.7, up to 5 per direction, never padded).

Pure, repository-only. No network/provider/credentials. Consumes validated
completed 15m `Bar` series (one per symbol + the Nifty 50 benchmark), an
explicit `TradingCalendar` (for session segmentation), and, for the Structure
dimension, an already-computed `StructureResult` from the 5m `structure.py`
engine.

**Cross-timeframe design disposition (review finding R4):** scoring the
Market Structure dimension from the 5m structure engine's state/BOS events is
not an implementation choice made here — it is what spec v0.3 §4.1 itself
specifies ("`structure.py`'s current state for the symbol ... BOS within the
last 3/4-10 completed 15m bars"). This module maps 5m-engine timestamps onto
the 15m ranking grid because the spec requires exactly that; it is not an
undocumented or reopened design decision. Whether this cross-timeframe
reference is predictive is a backtest question (§7), not a code-review one.

**Session-boundary correctness (review findings R1, R3):** structure state
and session VWAP must never carry across a session/gap boundary (both reset
per segment, matching `structure.py`'s own segmentation exactly — no new
segmentation definition is invented here). EMA, by contrast, is a smooth
rolling average that conventionally uses prior-session history to be
genuinely warm; it is **not** reset per segment, but a symbol is fail-closed
excluded (not partially scored) whenever EMA21 is not yet warm given the
supplied history.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from gate0.canonical_bars import Bar, validate_series
from gate0.indicators import ema, session_vwap
from gate0.nse_calendar import TradingCalendar
from gate0.structure import BOS_DOWN, BOS_UP, StructureResult, _segment

RS_INTERVALS_15M = (1, 2, 4)  # 15m, 30m, 60m expressed in 15m-bar offsets
RS_DEFAULT_THRESHOLD_PCT = Decimal("0.15")
QUALIFYING_FLOOR_DEFAULT = 45  # out of 90, provisional (spec §4.4) -- configurable via score_symbol's caller
NEUTRAL_BAND_DEFAULT = 5  # score points, provisional (spec §4.4) -- configurable via resolve_neutral_band's `band`
EMA_TREND_PERIOD = 9
EMA_SLOW_PERIOD = 21


class RankingInputError(ValueError):
    """Fail-closed: malformed input (wrong timeframe, bad direction, etc.)."""


def _require_15m(bars: list[Bar]) -> None:
    if any(b.timeframe != "15m" for b in bars):
        raise RankingInputError("ranking.py operates on 15m bars only (R2)")


@dataclass(frozen=True)
class DimensionDetail:
    rs_score: int
    rs_intervals: tuple[tuple[int, Decimal | None], ...]  # (bars_back, pct_diff or None)
    trend_momentum_score: int
    trend_sub: int
    momentum_sub: int
    structure_score: int
    structure_state_sub: int
    structure_recency_sub: int
    volume_flag: str  # "unavailable" | "available"
    volume_ratio: float | None  # current / baseline, None if unavailable (R5)
    total: int  # rs + trend_momentum + structure (0-90)


@dataclass(frozen=True)
class SymbolScore:
    symbol: str
    direction: str  # "up" | "down"
    detail: DimensionDetail
    eligible: bool  # cleared the qualifying floor (before neutral-band resolution)


def _pct_return(closes: list[float], i: int, bars_back: int) -> Decimal | None:
    if i - bars_back < 0:
        return None
    then = Decimal(str(closes[i - bars_back]))
    now = Decimal(str(closes[i]))
    if then == 0:
        return None
    return (now - then) / then * Decimal(100)


def rs_score(
    stock_bars: list[Bar],
    nifty_bars: list[Bar],
    *,
    index: int,
    direction: str,
    threshold_pct: Decimal = RS_DEFAULT_THRESHOLD_PCT,
) -> tuple[int, tuple[tuple[int, Decimal | None], ...]] | None:
    """§4.1 Relative strength: 10 pts per matched interval where sign agrees
    with direction and |diff| >= threshold. Max 30.

    **R2 fix:** compares `Bar` objects, not raw float arrays, and verifies
    that the stock/Nifty bars being compared at both the "now" and "then"
    positions of every interval have **exactly matching timestamps** before
    using them. Returns None (the whole symbol is unavailable for this
    dimension) the moment any required interval cannot be timestamp-matched
    — a missing candle on either side must never silently shift array
    positions and produce a wrong score.
    """
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    _require_15m(stock_bars)
    _require_15m(nifty_bars)
    if index >= len(stock_bars) or index >= len(nifty_bars):
        return None
    if stock_bars[index].bar_start_ts != nifty_bars[index].bar_start_ts:
        return None  # not even the "now" bars line up

    stock_closes = [b.close for b in stock_bars]
    nifty_closes = [b.close for b in nifty_bars]

    score = 0
    intervals: list[tuple[int, Decimal | None]] = []
    for bars_back in RS_INTERVALS_15M:
        then_idx = index - bars_back
        if then_idx < 0 or then_idx >= len(nifty_bars):
            return None  # required interval unavailable -> exclude the symbol (per R2)
        if stock_bars[then_idx].bar_start_ts != nifty_bars[then_idx].bar_start_ts:
            return None  # timestamps don't match at the "then" position -> exclude
        stock_ret = _pct_return(stock_closes, index, bars_back)
        nifty_ret = _pct_return(nifty_closes, index, bars_back)
        if stock_ret is None or nifty_ret is None:
            return None
        diff = stock_ret - nifty_ret
        intervals.append((bars_back, diff))
        agrees = diff > 0 if direction == "up" else diff < 0
        if agrees and abs(diff) >= threshold_pct:
            score += 10
    return score, tuple(intervals)


def trend_score(
    bars: list[Bar],
    *,
    index: int,
    direction: str,
    calendar: TradingCalendar,
) -> tuple[int, int, int] | None:
    """§4.1 Trend+Momentum (merged): returns (total 0-30, trend_sub 0/15,
    momentum_sub 0/8/15), or **None if EMA21 is not yet warm** (R3 fix: this
    used to silently score 0 trend points and still return a valid total;
    now the whole symbol is excluded, per §4.3's "never score with partial
    data").

    EMA uses the full available `bars[0..index]` history, deliberately **not**
    reset at session boundaries (a smooth rolling average is conventionally
    carried across sessions to be genuinely warm). Session VWAP, by contrast,
    **is** reset to the current session only (R1/R3 fix), via the same
    segmentation `structure.py` already uses — no new definition invented.
    """
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    _require_15m(bars)
    window = bars[: index + 1]
    closes = [b.close for b in window]

    ema9 = ema(closes, EMA_TREND_PERIOD)
    ema21 = ema(closes, EMA_SLOW_PERIOD)
    if ema9[index] is None or ema21[index] is None:
        return None  # EMA21 not warm -> fail closed, not a silent zero (R3)

    segments = _segment(window, calendar, "15m")
    current_segment = segments[-1] if segments else window
    vwap = session_vwap(current_segment)
    seg_local_index = len(current_segment) - 1
    if vwap[seg_local_index] is None:
        return None  # no valid volume yet this session -> fail closed

    ema_ok = (ema9[index] > ema21[index]) if direction == "up" else (ema9[index] < ema21[index])
    price_ok = (closes[index] > vwap[seg_local_index]) if direction == "up" else (closes[index] < vwap[seg_local_index])
    trend_sub = 15 if (ema_ok and price_ok) else 0

    momentum_sub = 0
    if index >= 6:
        recent = closes[index] - closes[index - 3]
        prior = closes[index - 3] - closes[index - 6]
        agrees = recent > 0 if direction == "up" else recent < 0
        if agrees:
            momentum_sub = 15 if abs(recent) > abs(prior) else 8
    return trend_sub + momentum_sub, trend_sub, momentum_sub


def _bars_back_15m(bos_ts: datetime, bars: list[Bar], as_of_index: int) -> int | None:
    """How many 15m bars back (0 = the as-of bar itself) a BOS timestamp falls,
    by locating the 15m bar whose window strictly contains it. None if no bar
    in bars[0..as_of_index] contains it (e.g., the BOS predates the segment)."""
    for j in range(as_of_index, -1, -1):
        if bars[j].bar_start_ts <= bos_ts < bars[j].bar_end_ts:
            return as_of_index - j
    return None


def structure_score(
    structure: StructureResult,
    bars_15m: list[Bar],
    *,
    index: int,
    direction: str,
    calendar: TradingCalendar,
) -> tuple[int, int, int]:
    """§4.1 Market structure: returns (total 0-30, state_sub 0/15, recency_sub 0/15/8/0).

    **R1 fix:** structure state and BOS recency are derived **only from events
    within the current session segment** (the segment containing the as-of
    15m bar) — a BOS from a prior session/gap segment can no longer leak into
    today's state. Uses the same segmentation `structure.py` itself applies;
    no new definition invented. No look-ahead: only events strictly before
    the as-of bar's close are considered.
    """
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    _require_15m(bars_15m)
    window = bars_15m[: index + 1]
    segments = _segment(window, calendar, "15m")
    current_segment = segments[-1] if segments else window
    segment_start_ts = current_segment[0].bar_start_ts
    as_of_ts = bars_15m[index].bar_end_ts

    relevant = [e for e in structure.events if segment_start_ts <= e.bar_start_ts < as_of_ts]
    state = "NEUTRAL"
    last_bos_ts: datetime | None = None
    last_bos_dir: str | None = None
    for ev in sorted(relevant, key=lambda e: e.bar_start_ts):
        if ev.type in ("BOS_UP", "CHOCH_UP"):
            state = "BULL"
        elif ev.type in ("BOS_DOWN", "CHOCH_DOWN"):
            state = "BEAR"
        if ev.type in (BOS_UP, BOS_DOWN):
            last_bos_ts = ev.bar_start_ts
            last_bos_dir = "up" if ev.type == BOS_UP else "down"

    state_sub = 15 if (state == "BULL" and direction == "up") or (state == "BEAR" and direction == "down") else 0

    recency_sub = 0
    if last_bos_ts is not None and last_bos_dir == direction:
        back = _bars_back_15m(last_bos_ts, bars_15m, index)
        if back is not None:
            if back <= 3:
                recency_sub = 15
            elif back <= 10:
                recency_sub = 8
    if state_sub == 0:
        recency_sub = 0  # state disagreement zeroes the whole dimension per spec

    return state_sub + recency_sub, state_sub, recency_sub


def score_symbol(
    symbol: str,
    direction: str,
    *,
    stock_bars_15m: list[Bar],
    nifty_bars_15m: list[Bar],
    structure: StructureResult,
    index: int,
    calendar: TradingCalendar,
    volume_baseline: float | None = None,
    rs_threshold_pct: Decimal = RS_DEFAULT_THRESHOLD_PCT,
    qualifying_floor: int = QUALIFYING_FLOOR_DEFAULT,
) -> SymbolScore | None:
    """§4.3: returns None (UNAVAILABLE) if any required scoring input is
    invalid, misaligned, or not yet warm -- never scores with partial data.
    """
    _require_15m(stock_bars_15m)
    _require_15m(nifty_bars_15m)
    if validate_series(stock_bars_15m[: index + 1], require_complete=True):
        return None
    if len(nifty_bars_15m) <= index or validate_series(nifty_bars_15m[: index + 1], require_complete=True):
        return None

    rs_result = rs_score(stock_bars_15m, nifty_bars_15m, index=index, direction=direction, threshold_pct=rs_threshold_pct)
    if rs_result is None:
        return None  # R2: misaligned/missing RS interval -> whole symbol unavailable
    rs, rs_detail = rs_result

    tm_result = trend_score(stock_bars_15m, index=index, direction=direction, calendar=calendar)
    if tm_result is None:
        return None  # R3: EMA21 not warm (or VWAP unavailable) -> whole symbol unavailable
    tm, trend_sub, momentum_sub = tm_result

    st, state_sub, recency_sub = structure_score(structure, stock_bars_15m, index=index, direction=direction, calendar=calendar)

    volume_ratio: float | None = None
    vol_flag = "unavailable"
    if volume_baseline is not None and volume_baseline > 0:
        volume_ratio = stock_bars_15m[index].volume / volume_baseline  # R5: preserve magnitude
        vol_flag = "available"

    total = rs + tm + st
    detail = DimensionDetail(
        rs_score=rs, rs_intervals=rs_detail,
        trend_momentum_score=tm, trend_sub=trend_sub, momentum_sub=momentum_sub,
        structure_score=st, structure_state_sub=state_sub, structure_recency_sub=recency_sub,
        volume_flag=vol_flag, volume_ratio=volume_ratio, total=total,
    )
    return SymbolScore(symbol=symbol, direction=direction, detail=detail,
                       eligible=total >= qualifying_floor)


def resolve_neutral_band(
    bull: SymbolScore | None,
    bear: SymbolScore | None,
    *,
    band: int = NEUTRAL_BAND_DEFAULT,
) -> tuple[bool, bool]:
    """§4.4, corrected logic: returns (bullish_included, bearish_included).
    `band` is explicitly a provisional, configurable value (R6) -- the
    module-level default is not a locked production threshold.

    - Only one side eligible -> that side only.
    - Both eligible, difference < band -> ambiguous, excluded from both.
    - Both eligible, difference >= band -> stronger direction only.
    """
    bull_ok = bull is not None and bull.eligible
    bear_ok = bear is not None and bear.eligible
    if bull_ok and not bear_ok:
        return True, False
    if bear_ok and not bull_ok:
        return False, True
    if not bull_ok and not bear_ok:
        return False, False
    # both eligible
    diff = abs(bull.detail.total - bear.detail.total)  # type: ignore[union-attr]
    if diff < band:
        return False, False  # ambiguous
    if bull.detail.total > bear.detail.total:  # type: ignore[union-attr]
        return True, False
    return False, True


@dataclass(frozen=True)
class Shortlist:
    bullish: tuple[SymbolScore, ...] = field(default_factory=tuple)
    bearish: tuple[SymbolScore, ...] = field(default_factory=tuple)


def build_shortlist(scores: list[tuple[SymbolScore | None, SymbolScore | None]], *, max_per_side: int = 5) -> Shortlist:
    """§4.7: up to `max_per_side` per direction, ranked by total score
    descending, ties broken by **relative-volume magnitude** (R5: higher
    ratio ranks first; unavailable sorts after any available ratio) then
    alphabetically (display only). Never pads. `scores` is a list of
    (bull_score_or_None, bear_score_or_None) pairs, already neutral-band-
    resolved by the caller."""
    def _sort_key(s: SymbolScore) -> tuple:
        has_ratio = s.detail.volume_ratio is not None
        ratio_rank = -s.detail.volume_ratio if has_ratio else 0.0
        return (-s.detail.total, 0 if has_ratio else 1, ratio_rank, s.symbol)

    bulls = sorted((b for b, _ in scores if b is not None), key=_sort_key)[:max_per_side]
    bears = sorted((b for _, b in scores if b is not None), key=_sort_key)[:max_per_side]
    return Shortlist(bullish=tuple(bulls), bearish=tuple(bears))

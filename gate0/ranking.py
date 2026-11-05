"""Stage 1 directional ranking (15m) — Gate 0 harness, Phase A.

Implements spec v0.3 §4 in full: the three mandatory scored dimensions
(relative strength, trend+momentum, market structure — 0-30 each, 90 total),
the optional volume tiebreak modifier (§4.2), missing-data exclusion (§4.3),
the qualifying floor + corrected neutral-band resolution (§4.4), and the
Stage 1 shortlist (§4.7, up to 5 per direction, never padded).

Pure, repository-only. No network/provider/credentials. Consumes validated
completed 15m `Bar` series (one per symbol + the Nifty 50 benchmark) and,
for the Structure dimension, an already-computed `StructureResult` from the
5m `structure.py` engine (structure confirmation is a 5m-engine output used
as a 15m ranking *input* — this is the intended cross-timeframe design, not
a mismatch: §4.1 explicitly scores it against "the last 3/4-10 completed 15m
bars", so BOS timestamps are mapped onto the 15m bar grid here).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from gate0.canonical_bars import Bar, validate_series
from gate0.indicators import ema, session_vwap
from gate0.structure import BOS_DOWN, BOS_UP, StructureResult

RS_INTERVALS_15M = (1, 2, 4)  # 15m, 30m, 60m expressed in 15m-bar offsets
RS_DEFAULT_THRESHOLD_PCT = Decimal("0.15")
QUALIFYING_FLOOR_DEFAULT = 45  # out of 90, provisional (spec §4.4)
NEUTRAL_BAND_DEFAULT = 5  # score points, provisional (spec §4.4)


class RankingInputError(ValueError):
    """Fail-closed: malformed/insufficient input for scoring."""


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
    volume_flag: str  # "unavailable" | "above_baseline" | "below_baseline"
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
    stock_closes: list[float],
    nifty_closes: list[float],
    *,
    index: int,
    direction: str,
    threshold_pct: Decimal = RS_DEFAULT_THRESHOLD_PCT,
) -> tuple[int, tuple[tuple[int, Decimal | None], ...]]:
    """§4.1 Relative strength: 10 pts per matched interval where sign agrees
    with direction and |diff| >= threshold. Max 30."""
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    score = 0
    intervals: list[tuple[int, Decimal | None]] = []
    for bars_back in RS_INTERVALS_15M:
        stock_ret = _pct_return(stock_closes, index, bars_back)
        nifty_ret = _pct_return(nifty_closes, index, bars_back)
        if stock_ret is None or nifty_ret is None:
            intervals.append((bars_back, None))
            continue
        diff = stock_ret - nifty_ret
        intervals.append((bars_back, diff))
        agrees = diff > 0 if direction == "up" else diff < 0
        if agrees and abs(diff) >= threshold_pct:
            score += 10
    return score, tuple(intervals)


def trend_score(bars: list[Bar], *, index: int, direction: str) -> tuple[int, int, int]:
    """§4.1 Trend+Momentum (merged): returns (total 0-30, trend_sub 0/15,
    momentum_sub 0/8/15). `bars` must be one contiguous session segment
    (caller's responsibility, consistent with structure.py's segmentation);
    `index` is the bar to score as-of (uses only bars[0..index])."""
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    closes = [b.close for b in bars[: index + 1]]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    vwap = session_vwap(bars[: index + 1])

    trend_sub = 0
    if ema9[index] is not None and ema21[index] is not None and vwap[index] is not None:
        ema_ok = (ema9[index] > ema21[index]) if direction == "up" else (ema9[index] < ema21[index])
        price_ok = (closes[index] > vwap[index]) if direction == "up" else (closes[index] < vwap[index])
        if ema_ok and price_ok:
            trend_sub = 15

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
) -> tuple[int, int, int]:
    """§4.1 Market structure: returns (total 0-30, state_sub 0/15, recency_sub 0/15/8/0).

    Current state is derived from the last structure event at/before the
    as-of 15m bar's end (no look-ahead): the most recent BOS_UP/CHOCH_UP ->
    BULL, BOS_DOWN/CHOCH_DOWN -> BEAR, none -> NEUTRAL.
    """
    if direction not in ("up", "down"):
        raise RankingInputError(f"invalid direction: {direction}")
    as_of_ts = bars_15m[index].bar_end_ts

    relevant = [e for e in structure.events if e.bar_start_ts < as_of_ts]
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
    volume_baseline: float | None = None,
    rs_threshold_pct: Decimal = RS_DEFAULT_THRESHOLD_PCT,
) -> SymbolScore | None:
    """§4.3: returns None (UNAVAILABLE) if required inputs are invalid/missing
    -- never scores with partial data."""
    if validate_series(stock_bars_15m[: index + 1], require_complete=True):
        return None
    if len(nifty_bars_15m) <= index or validate_series(nifty_bars_15m[: index + 1], require_complete=True):
        return None
    if index < 6:  # momentum needs 6 prior bars; treat as not-yet-warm, not an error
        return None

    stock_closes = [b.close for b in stock_bars_15m]
    nifty_closes = [b.close for b in nifty_bars_15m]

    rs, rs_detail = rs_score(stock_closes, nifty_closes, index=index, direction=direction, threshold_pct=rs_threshold_pct)
    tm, trend_sub, momentum_sub = trend_score(stock_bars_15m, index=index, direction=direction)
    st, state_sub, recency_sub = structure_score(structure, stock_bars_15m, index=index, direction=direction)

    if volume_baseline is None or volume_baseline <= 0:
        vol_flag = "unavailable"
    else:
        vol_flag = "above_baseline" if stock_bars_15m[index].volume > volume_baseline else "below_baseline"

    total = rs + tm + st
    detail = DimensionDetail(
        rs_score=rs, rs_intervals=rs_detail,
        trend_momentum_score=tm, trend_sub=trend_sub, momentum_sub=momentum_sub,
        structure_score=st, structure_state_sub=state_sub, structure_recency_sub=recency_sub,
        volume_flag=vol_flag, total=total,
    )
    return SymbolScore(symbol=symbol, direction=direction, detail=detail,
                       eligible=total >= QUALIFYING_FLOOR_DEFAULT)


def resolve_neutral_band(
    bull: SymbolScore | None,
    bear: SymbolScore | None,
    *,
    band: int = NEUTRAL_BAND_DEFAULT,
) -> tuple[bool, bool]:
    """§4.4, corrected logic: returns (bullish_included, bearish_included).

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
    descending, ties broken by volume modifier then alphabetically (display
    only). Never pads. `scores` is a list of (bull_score_or_None, bear_score_or_None)
    pairs, one per symbol, already neutral-band-resolved by the caller
    (i.e. a side set to None here means "not included this scan")."""
    def _sort_key(s: SymbolScore) -> tuple:
        vol_rank = {"above_baseline": 0, "unavailable": 1, "below_baseline": 2}[s.detail.volume_flag]
        return (-s.detail.total, vol_rank, s.symbol)

    bulls = sorted((b for b, _ in scores if b is not None), key=_sort_key)[:max_per_side]
    bears = sorted((b for _, b in scores if b is not None), key=_sort_key)[:max_per_side]
    return Shortlist(bullish=tuple(bulls), bearish=tuple(bears))

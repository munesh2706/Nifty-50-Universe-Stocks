"""Canonical OHLCV bar model and validation (Gate 0 harness, Phase A).

Pure functions only. No network, no provider calls, no real market data.
Implements the canonical-bar schema (spec v0.2 §3.2), the data-quality checks
(§3.3) and the 5m->15m aggregation contract (§4A.4 scope rule): a 15m bar is
complete only when all three constituent 5m bars are valid; any absence
propagates upward as "unavailable", never fabricated.

This harness is a disposable audit tool; its language (Python) is not a
production-stack decision (spec §14 remains open).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))  # Asia/Kolkata (fixed offset; India has no DST)

TIMEFRAME_MINUTES = {"5m": 5, "15m": 15}


@dataclass(frozen=True)
class Bar:
    """One completed OHLCV candle in the canonical schema (§3.2)."""

    instrument_id: str
    timeframe: str  # "5m" | "15m"
    bar_start_ts: datetime  # timezone-aware
    bar_end_ts: datetime  # timezone-aware
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_complete: bool = True
    quality_flags: tuple[str, ...] = field(default_factory=tuple)


def validate_bar(bar: Bar) -> list[str]:
    """Return a list of problem codes for a single bar; empty list == valid.

    Fail-closed: any structural problem is reported rather than silently fixed.
    """
    problems: list[str] = []

    if bar.timeframe not in TIMEFRAME_MINUTES:
        problems.append("UNKNOWN_TIMEFRAME")

    if bar.bar_start_ts.tzinfo is None or bar.bar_end_ts.tzinfo is None:
        problems.append("NAIVE_TIMESTAMP")
    else:
        expected = TIMEFRAME_MINUTES.get(bar.timeframe)
        if expected is not None:
            if bar.bar_end_ts - bar.bar_start_ts != timedelta(minutes=expected):
                problems.append("BAD_BAR_DURATION")

    # Price positivity (reject zero/negative — §3.3).
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        problems.append("NON_POSITIVE_PRICE")

    # OHLC relationships (§3.3): high is the max, low is the min.
    if bar.high < max(bar.open, bar.close, bar.low):
        problems.append("HIGH_NOT_MAX")
    if bar.low > min(bar.open, bar.close, bar.high):
        problems.append("LOW_NOT_MIN")

    if bar.volume < 0:
        problems.append("NEGATIVE_VOLUME")

    return problems


def validate_series(bars: list[Bar]) -> list[str]:
    """Validate an ordered series for one instrument+timeframe.

    Checks per-bar validity, strict chronological ordering, and duplicate
    bar_start timestamps. Does NOT invent missing bars.
    """
    problems: list[str] = []
    if not bars:
        return problems

    instruments = {b.instrument_id for b in bars}
    timeframes = {b.timeframe for b in bars}
    if len(instruments) != 1:
        problems.append("MIXED_INSTRUMENTS")
    if len(timeframes) != 1:
        problems.append("MIXED_TIMEFRAMES")

    for i, b in enumerate(bars):
        problems.extend(f"{b.bar_start_ts.isoformat()}:{p}" for p in validate_bar(b))
        if i > 0:
            prev = bars[i - 1]
            if b.bar_start_ts == prev.bar_start_ts:
                problems.append(f"DUPLICATE_BAR_START:{b.bar_start_ts.isoformat()}")
            elif b.bar_start_ts < prev.bar_start_ts:
                problems.append(f"OUT_OF_ORDER:{b.bar_start_ts.isoformat()}")

    return problems


def aggregate_5m_to_15m(five_min_bars: list[Bar | None]) -> Bar | None:
    """Aggregate exactly three consecutive 5m bars into one 15m bar.

    Returns None (UNAVAILABLE) if fewer than three valid, contiguous, in-order
    5m bars are supplied — the absence propagates upward and must NOT be
    fabricated (§4A.4). A None in the input represents a known-missing 5m bar.
    """
    if len(five_min_bars) != 3 or any(b is None for b in five_min_bars):
        return None
    bars: list[Bar] = [b for b in five_min_bars if b is not None]

    if any(b.timeframe != "5m" for b in bars):
        return None
    if len({b.instrument_id for b in bars}) != 1:
        return None
    if validate_series(bars):
        return None
    # Contiguity: each bar starts where the previous ended.
    for prev, nxt in zip(bars, bars[1:]):
        if nxt.bar_start_ts != prev.bar_end_ts:
            return None

    return Bar(
        instrument_id=bars[0].instrument_id,
        timeframe="15m",
        bar_start_ts=bars[0].bar_start_ts,
        bar_end_ts=bars[2].bar_end_ts,
        open=bars[0].open,
        high=max(b.high for b in bars),
        low=min(b.low for b in bars),
        close=bars[2].close,
        volume=sum(b.volume for b in bars),
        is_complete=all(b.is_complete for b in bars),
        quality_flags=("AGGREGATED_FROM_5M",),
    )

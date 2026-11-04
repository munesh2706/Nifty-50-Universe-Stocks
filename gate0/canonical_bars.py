"""Canonical OHLCV bar model and validation (Gate 0 harness, Phase A).

Pure functions only. No network, no provider calls, no real market data.
Implements a validation DTO for the canonical-bar schema (spec v0.2 §3.2), the
data-quality checks (§3.3), the completed-bar contract, exchange-time alignment
and the 5m->15m aggregation contract (§4A.4 scope): a 15m bar is complete only
when all three constituent 5m bars are valid, complete and bucket-aligned; any
absence propagates upward as "unavailable", never fabricated.

NOTE (R3): this `Bar` carries the §3.2 fields but several (open_interest, source,
received_at) are optional metadata; `validate_bar` validates the OHLCV + timing
core. This is the canonical *validation* model, not yet the full ingestion model.

This harness is a disposable audit tool; its language (Python) is not a
production-stack decision (spec §14 remains open).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))  # Asia/Kolkata (fixed offset; India has no DST)
IST_OFFSET = timedelta(hours=5, minutes=30)
SESSION_OPEN = time(9, 15)  # NSE regular session open (IST); holidays handled by nse_calendar later

TIMEFRAME_MINUTES = {"5m": 5, "15m": 15}


@dataclass(frozen=True)
class Bar:
    """One OHLCV candle in the canonical schema (§3.2)."""

    instrument_id: str
    timeframe: str  # "5m" | "15m"
    bar_start_ts: datetime  # timezone-aware, Asia/Kolkata
    bar_end_ts: datetime  # timezone-aware, Asia/Kolkata
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_complete: bool = True
    # §3.2 metadata (optional in this validation DTO — R3):
    underlying_symbol: str | None = None
    exchange: str | None = None
    open_interest: float | None = None
    source: str | None = None
    received_at: datetime | None = None
    quality_flags: tuple[str, ...] = field(default_factory=tuple)


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def minutes_since_open(ts: datetime) -> float | None:
    """Minutes from the session open (09:15 IST) of ts's date. None if not tz-aware."""
    if ts.tzinfo is None:
        return None
    local = ts.astimezone(IST)
    open_dt = datetime.combine(local.date(), SESSION_OPEN, tzinfo=IST)
    return (local - open_dt).total_seconds() / 60.0


def validate_bar(bar: Bar, *, require_complete: bool = True) -> list[str]:
    """Return problem codes for a single bar; empty list == valid. Fail-closed.

    With require_complete=True (the canonical completed-bar path), an incomplete
    (forming) bar is rejected. Pass require_complete=False for a provisional
    display path.
    """
    problems: list[str] = []

    if not bar.instrument_id:
        problems.append("EMPTY_INSTRUMENT_ID")

    if bar.timeframe not in TIMEFRAME_MINUTES:
        problems.append("UNKNOWN_TIMEFRAME")

    # R1 — non-finite values must be rejected before any relational check.
    if not _finite(bar.open, bar.high, bar.low, bar.close, bar.volume):
        problems.append("NON_FINITE_VALUE")
        return problems  # relational checks are meaningless with NaN/inf present

    # R5 — timezone must represent Asia/Kolkata (+05:30), not just "aware".
    if bar.bar_start_ts.tzinfo is None or bar.bar_end_ts.tzinfo is None:
        problems.append("NAIVE_TIMESTAMP")
    else:
        if bar.bar_start_ts.utcoffset() != IST_OFFSET or bar.bar_end_ts.utcoffset() != IST_OFFSET:
            problems.append("WRONG_TIMEZONE_OFFSET")
        expected = TIMEFRAME_MINUTES.get(bar.timeframe)
        if expected is not None:
            if bar.bar_end_ts - bar.bar_start_ts != timedelta(minutes=expected):
                problems.append("BAD_BAR_DURATION")
            # R4 — bucket alignment to the session grid.
            mso = minutes_since_open(bar.bar_start_ts)
            if mso is None or mso < 0:
                problems.append("BEFORE_SESSION_OPEN")
            elif mso % expected != 0:
                problems.append("MISALIGNED_BAR_START")

    # R2 — completed-bar contract.
    if require_complete and not bar.is_complete:
        problems.append("INCOMPLETE_BAR")

    # §3.3 price positivity.
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        problems.append("NON_POSITIVE_PRICE")

    # §3.3 OHLC relationships: high is the max, low is the min.
    if bar.high < max(bar.open, bar.close, bar.low):
        problems.append("HIGH_NOT_MAX")
    if bar.low > min(bar.open, bar.close, bar.high):
        problems.append("LOW_NOT_MIN")

    if bar.volume < 0:
        problems.append("NEGATIVE_VOLUME")

    if bar.open_interest is not None and (not _finite(bar.open_interest) or bar.open_interest < 0):
        problems.append("BAD_OPEN_INTEREST")

    return problems


def validate_series(bars: list[Bar], *, require_complete: bool = True) -> list[str]:
    """Validate an ordered series for one instrument+timeframe.

    Per-bar validity, strict chronological order, duplicate bar_start detection.
    Does NOT invent missing bars and does NOT verify expected coverage — an empty
    series returns [] and callers must separately enforce expected coverage
    (a calendar/recovery responsibility).
    """
    problems: list[str] = []
    if not bars:
        return problems

    if len({b.instrument_id for b in bars}) != 1:
        problems.append("MIXED_INSTRUMENTS")
    if len({b.timeframe for b in bars}) != 1:
        problems.append("MIXED_TIMEFRAMES")

    for i, b in enumerate(bars):
        problems.extend(
            f"{b.bar_start_ts.isoformat()}:{p}" for p in validate_bar(b, require_complete=require_complete)
        )
        if i > 0:
            prev = bars[i - 1]
            if b.bar_start_ts == prev.bar_start_ts:
                problems.append(f"DUPLICATE_BAR_START:{b.bar_start_ts.isoformat()}")
            elif b.bar_start_ts < prev.bar_start_ts:
                problems.append(f"OUT_OF_ORDER:{b.bar_start_ts.isoformat()}")

    return problems


def aggregate_5m_to_15m(five_min_bars: list[Bar | None]) -> Bar | None:
    """Aggregate exactly three consecutive, complete, 15m-bucket-aligned 5m bars.

    Returns None (UNAVAILABLE) unless all of: exactly three inputs, none None,
    all 5m, same instrument, all valid+complete, contiguous, and the first bar
    starts on a 15m session-grid boundary (§4A.4; R2, R4). Never fabricates.
    """
    if len(five_min_bars) != 3 or any(b is None for b in five_min_bars):
        return None
    bars: list[Bar] = [b for b in five_min_bars if b is not None]

    if any(b.timeframe != "5m" for b in bars):
        return None
    if len({b.instrument_id for b in bars}) != 1:
        return None
    if validate_series(bars, require_complete=True):  # rejects incomplete/invalid/misaligned
        return None
    if not all(b.is_complete for b in bars):
        return None
    # Contiguity: each bar starts where the previous ended.
    for prev, nxt in zip(bars, bars[1:]):
        if nxt.bar_start_ts != prev.bar_end_ts:
            return None
    # R4 — the 15m bar must start on a 15m session-grid boundary.
    mso = minutes_since_open(bars[0].bar_start_ts)
    if mso is None or mso < 0 or mso % 15 != 0:
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
        is_complete=True,
        underlying_symbol=bars[0].underlying_symbol,
        exchange=bars[0].exchange,
        quality_flags=("AGGREGATED_FROM_5M",),
    )

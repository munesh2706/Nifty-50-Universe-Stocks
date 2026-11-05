"""Synthetic, clearly-labelled bar fixtures for Phase A tests.

NOT real market data. These builders produce deterministic fake candles so the
pure validation/aggregation logic can be tested with no provider contact.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from gate0.canonical_bars import IST, TIMEFRAME_MINUTES, Bar


def make_bar(
    instrument_id: str = "SYNTH",
    timeframe: str = "5m",
    start: datetime | None = None,
    o: float = 100.0,
    h: float = 101.0,
    low: float = 99.0,
    c: float = 100.5,
    volume: float = 1000.0,
    is_complete: bool = True,
    open_interest: float | None = None,
) -> Bar:
    if start is None:
        start = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
    minutes = TIMEFRAME_MINUTES.get(timeframe, 5)
    return Bar(
        instrument_id=instrument_id,
        timeframe=timeframe,
        bar_start_ts=start,
        bar_end_ts=start + timedelta(minutes=minutes),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=volume,
        is_complete=is_complete,
        open_interest=open_interest,
    )


def make_5m_run(n: int, instrument_id: str = "SYNTH", start: datetime | None = None) -> list[Bar]:
    """n contiguous, valid 5m bars starting at `start` (default 09:15 IST)."""
    if start is None:
        start = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
    out: list[Bar] = []
    cur = start
    for i in range(n):
        base = 100.0 + i
        out.append(
            make_bar(
                instrument_id=instrument_id,
                timeframe="5m",
                start=cur,
                o=base,
                h=base + 1.0,
                low=base - 1.0,
                c=base + 0.5,
            )
        )
        cur += timedelta(minutes=5)
    return out

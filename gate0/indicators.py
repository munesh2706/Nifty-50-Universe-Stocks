"""Deterministic indicator primitives (Gate 0 harness, Phase A) — EMA and VWAP.

Pure functions only. No network, no provider calls. Used by `ranking.py`'s
Trend sub-score (spec v0.3 §4.1).
"""
from __future__ import annotations

from gate0.canonical_bars import Bar


def ema(values: list[float], period: int) -> list[float | None]:
    """Standard EMA. Seeded with the SMA of the first `period` values; None
    for indices before the seed (warm-up). Deterministic, no look-ahead:
    ema[i] uses only values[0..i].
    """
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    k = 2.0 / (period + 1)
    prev = seed
    for i in range(period, len(values)):
        prev = (values[i] - prev) * k + prev
        out[i] = prev
    return out


def session_vwap(bars: list[Bar]) -> list[float | None]:
    """Cumulative typical-price VWAP within ONE contiguous bar series
    (caller passes one session segment at a time — no reset logic here).
    vwap[i] uses only bars[0..i] (no look-ahead).
    """
    out: list[float | None] = [None] * len(bars)
    cum_pv = 0.0
    cum_vol = 0.0
    for i, b in enumerate(bars):
        typical = (b.high + b.low + b.close) / 3.0
        cum_pv += typical * b.volume
        cum_vol += b.volume
        out[i] = (cum_pv / cum_vol) if cum_vol > 0 else None
    return out

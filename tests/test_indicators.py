"""Phase A unit tests for gate0.indicators (EMA, session VWAP). Synthetic only."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.indicators import ema, session_vwap

START = datetime(2026, 11, 4, 9, 15, tzinfo=IST)


def make_bars15(closes, volumes=None, start=START):
    bars = []
    cur = start
    volumes = volumes or [1000.0] * len(closes)
    for c, v in zip(closes, volumes):
        bars.append(Bar("SYNTH", "15m", cur, cur + timedelta(minutes=15), c, c + 1, c - 1, c, v))
        cur += timedelta(minutes=15)
    return bars


def test_ema_warmup_none_before_period():
    vals = [100.0] * 8 + [101.0]
    result = ema(vals, 9)
    assert all(v is None for v in result[:8])
    assert result[8] is not None


def test_ema_seed_is_sma():
    vals = [1.0, 2.0, 3.0]
    result = ema(vals, 3)
    assert result[2] == pytest.approx(2.0)


def test_ema_update_formula():
    vals = [1.0, 2.0, 3.0, 10.0]
    result = ema(vals, 3)
    k = 2.0 / 4
    expected = (10.0 - 2.0) * k + 2.0
    assert result[3] == pytest.approx(expected)


def test_ema_no_look_ahead():
    vals = [1.0, 2.0, 3.0]
    full = ema(vals, 3)
    truncated = ema(vals[:3], 3)
    assert full[2] == truncated[2]


def test_vwap_increasing_with_uniform_volume():
    bars = make_bars15([100, 101, 102])
    v = session_vwap(bars)
    assert v[0] is not None
    # VWAP should track the rising typical prices
    assert v[0] < v[1] < v[2]


def test_vwap_zero_volume_is_none():
    bars = make_bars15([100, 101], volumes=[0.0, 0.0])
    v = session_vwap(bars)
    assert v == [None, None]

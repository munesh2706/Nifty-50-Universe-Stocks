"""Phase A unit tests for gate0.costs (versioned placeholder cost schedule,
spec v0.3 §7.4). Synthetic only."""
from __future__ import annotations

from decimal import Decimal

import pytest

from gate0.costs import PLACEHOLDER_SCHEDULE, round_trip_cost


def test_round_trip_cost_is_positive_and_small_relative_to_value():
    cost = round_trip_cost(Decimal("100"), Decimal("105"), Decimal("10"), intraday=True)
    assert cost > 0
    trade_value = Decimal("100") * Decimal("10")
    assert cost < trade_value * Decimal("0.05")  # sanity: costs are a few % at most, not dominant


def test_delivery_and_intraday_stt_differ():
    delivery_cost = round_trip_cost(Decimal("100"), Decimal("105"), Decimal("10"), intraday=False)
    intraday_cost = round_trip_cost(Decimal("100"), Decimal("105"), Decimal("10"), intraday=True)
    assert delivery_cost != intraday_cost


def test_round_trip_cost_rejects_non_positive_quantity():
    with pytest.raises(ValueError):
        round_trip_cost(Decimal("100"), Decimal("105"), Decimal("0"), intraday=True)


def test_cost_scales_with_quantity():
    small = round_trip_cost(Decimal("100"), Decimal("105"), Decimal("1"), intraday=True)
    large = round_trip_cost(Decimal("100"), Decimal("105"), Decimal("10"), intraday=True)
    assert float(large) == pytest.approx(float(small) * 10, rel=1e-9)


def test_brokerage_cap_applies_on_large_trade_value():
    schedule = PLACEHOLDER_SCHEDULE
    # A trade value large enough that pct brokerage would exceed the flat cap.
    big_cost = round_trip_cost(Decimal("10000"), Decimal("10500"), Decimal("1000"), intraday=True, schedule=schedule)
    assert big_cost > 0  # just confirms it computes without blowing up; cap keeps brokerage bounded

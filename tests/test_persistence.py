"""Phase A unit tests for gate0.persistence (deterministic signal/backtest
record building, spec v0.3 §8). Synthetic only."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from gate0.backtest import TradeOutcome
from gate0.canonical_bars import IST
from gate0.persistence import build_signal_record, config_hash, config_snapshot, record_hash
from gate0.ranking import DimensionDetail, SymbolScore
from gate0.scan import ScanConfig
from gate0.setup import SetupEvaluation
from gate0.zones import STATE_TOUCHED, Zone

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)


def make_zone(**overrides) -> Zone:
    defaults = dict(
        zone_id="Z1", approach="B", direction="up", boundary_type="full_range",
        proximal=106.0, distal=103.0, anchor_bar_id=None, displacement_id="D1",
        created_ts=NORMAL, state=STATE_TOUCHED, touched_ts=NORMAL + timedelta(minutes=5),
        confirmed_ts=NORMAL + timedelta(minutes=10), invalidated_ts=None, expired_ts=None,
    )
    defaults.update(overrides)
    return Zone(**defaults)


def make_stage1_score(total=75) -> SymbolScore:
    detail = DimensionDetail(
        rs_score=30, rs_intervals=((1, Decimal("0.5")), (2, Decimal("1.0")), (4, Decimal("2.0"))),
        trend_momentum_score=30, trend_sub=15, momentum_sub=15,
        structure_score=15, structure_state_sub=15, structure_recency_sub=0,
        volume_flag="available", volume_ratio=1.5, total=total,
    )
    return SymbolScore(symbol="GOODSTOCK", direction="up", detail=detail, eligible=total >= 45)


def make_evaluation() -> SetupEvaluation:
    zone = make_zone()
    return SetupEvaluation(symbol="GOODSTOCK", direction="up", zone=zone, stage1_score=75,
                           entry_price=106.0, stop_price=103.0, target_price=115.5,
                           net_rr=3.17, eligible=True, reason_codes=(), bearish_status=None)


def make_outcome() -> TradeOutcome:
    return TradeOutcome(
        displacement_id="D1", approach="B", boundary_type="full_range", direction="up",
        outcome="WIN", fill_ts=NORMAL + timedelta(minutes=15), fill_price=106.1,
        exit_ts=NORMAL + timedelta(minutes=30), exit_price=115.5, stop_price=103.0,
        target_price=115.5, mae=1.2, net_rr_after_costs=2.9,
    )


# --- config_snapshot / config_hash ---

def test_config_snapshot_is_json_safe_and_stringifies_decimal():
    snap = config_snapshot(ScanConfig())
    assert isinstance(snap["rs_threshold_pct"], str)  # Decimal -> str, never silently floated
    assert snap["approach"] == "B"


def test_config_hash_identical_for_equal_configs():
    assert config_hash(ScanConfig()) == config_hash(ScanConfig())


def test_config_hash_differs_for_different_configs():
    assert config_hash(ScanConfig()) != config_hash(ScanConfig(approach="A"))


def test_config_hash_stable_regardless_of_dict_construction_order():
    # Decimal equality: Decimal("0.15") == Decimal("0.150") -- the hash must
    # agree too, since both represent the identical config value.
    a = ScanConfig(rs_threshold_pct=Decimal("0.15"))
    b = ScanConfig(rs_threshold_pct=Decimal("0.150"))
    assert config_hash(a) == config_hash(b)


# --- build_signal_record ---

def test_build_signal_record_is_deterministic():
    kwargs = dict(
        strategy_version="0.3.0", git_commit="94a63b5", config=ScanConfig(), symbol="GOODSTOCK",
        direction="up", stage1_score=make_stage1_score(), evaluation=make_evaluation(),
        bar_references=["2026-11-04T09:15:00+05:30", "2026-11-04T09:30:00+05:30"],
        trade_outcome=make_outcome(), cost_schedule_version="placeholder-v1-2026-11-06",
    )
    r1 = build_signal_record(**kwargs)
    r2 = build_signal_record(**kwargs)
    assert r1 == r2
    assert record_hash(r1) == record_hash(r2)


def test_build_signal_record_no_derivative_fields_exist():
    record = build_signal_record(
        strategy_version="0.3.0", git_commit="abc123", config=ScanConfig(), symbol="X", direction="up",
        stage1_score=None, evaluation=None, bar_references=[],
    )
    serialized = str(record).lower()
    for forbidden in ("strike", "expiry", "option", "future", "lot_size", "greek"):
        assert forbidden not in serialized


def test_build_signal_record_covers_required_sec8_fields():
    record = build_signal_record(
        strategy_version="0.3.0", git_commit="abc123", config=ScanConfig(), symbol="GOODSTOCK",
        direction="up", stage1_score=make_stage1_score(), evaluation=make_evaluation(),
        bar_references=["2026-11-04T09:15:00+05:30"], trade_outcome=make_outcome(),
        cost_schedule_version="placeholder-v1-2026-11-06",
    )
    assert record["strategy_version"] == "0.3.0"
    assert record["git_commit"] == "abc123"
    assert "config_snapshot" in record and "config_hash" in record
    assert record["input_bar_references"] == ["2026-11-04T09:15:00+05:30"]
    assert record["stage1"]["total"] == 75
    assert record["stage2"]["zone"]["approach"] == "B"
    assert record["stage2"]["zone"]["lifecycle"]["state"] == STATE_TOUCHED
    assert record["stage2"]["eligible"] is True
    assert record["cost_schedule_version"] == "placeholder-v1-2026-11-06"
    assert record["outcome"]["outcome"] == "WIN"


def test_build_signal_record_carries_bearish_status():
    # Review (ChatGPT, post-056): bearish_status must survive record creation.
    bearish_zone = make_zone(direction="down")
    bearish_eval = SetupEvaluation(symbol="BEARSTOCK", direction="down", zone=bearish_zone, stage1_score=60,
                                   entry_price=103.0, stop_price=106.0, target_price=94.0,
                                   net_rr=3.0, eligible=True, reason_codes=(), bearish_status="BEARISH_RESEARCH")
    record = build_signal_record(
        strategy_version="0.3.0", git_commit="abc123", config=ScanConfig(), symbol="BEARSTOCK",
        direction="down", stage1_score=None, evaluation=bearish_eval, bar_references=[],
    )
    assert record["stage2"]["bearish_status"] == "BEARISH_RESEARCH"


def test_build_signal_record_handles_missing_stage1_and_stage2_gracefully():
    record = build_signal_record(
        strategy_version="0.3.0", git_commit="abc123", config=ScanConfig(), symbol="X", direction="down",
        stage1_score=None, evaluation=None, bar_references=[],
    )
    assert record["stage1"] is None
    assert record["stage2"] is None
    assert record["outcome"] is None


def test_build_signal_record_rejects_invalid_direction():
    with pytest.raises(ValueError):
        build_signal_record(strategy_version="0.3.0", git_commit="abc123", config=ScanConfig(),
                            symbol="X", direction="sideways", stage1_score=None, evaluation=None,
                            bar_references=[])


def test_different_git_commit_changes_the_record_but_not_the_config_hash():
    base = dict(strategy_version="0.3.0", config=ScanConfig(), symbol="X", direction="up",
               stage1_score=None, evaluation=None, bar_references=[])
    r1 = build_signal_record(git_commit="aaa111", **base)
    r2 = build_signal_record(git_commit="bbb222", **base)
    assert r1["config_hash"] == r2["config_hash"]  # same config -> same hash
    assert record_hash(r1) != record_hash(r2)  # but the overall record differs

"""Phase A unit tests for gate0.setup (Stage 2 setup validation, spec v0.3
§4.8). Synthetic only. Zones are constructed directly to isolate Stage 2's
own evaluation/selection logic from zones.py's lifecycle mechanics."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from gate0.canonical_bars import IST
from gate0.setup import (
    BEARISH_EXECUTABLE_SHORT,
    BEARISH_RESEARCH,
    ENTRY_TOO_EXTENDED,
    NO_DIRECTIONAL_EDGE,
    NO_FRESH_SETUP,
    RR_BELOW_MINIMUM,
    ZONE_INVALIDATED,
    SetupInputError,
    evaluate_setup,
    select_final_candidates,
)
from gate0.zones import STATE_ACTIVE, STATE_EXPIRED, STATE_INVALIDATED, STATE_TOUCHED, Zone

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)


def make_zone(**overrides) -> Zone:
    defaults = dict(
        zone_id="Z1", approach="A", direction="up", boundary_type="full_range",
        proximal=106.0, distal=103.0, anchor_bar_id="anchor", displacement_id="D1",
        created_ts=NORMAL, state=STATE_ACTIVE, touched_ts=None, confirmed_ts=None,
        invalidated_ts=None, expired_ts=None,
    )
    defaults.update(overrides)
    return Zone(**defaults)


# --- Q1: directional confirmation ---

def test_q1_fails_when_structure_disagrees():
    zone = make_zone(confirmed_ts=NORMAL + timedelta(minutes=10), state=STATE_TOUCHED)
    result = evaluate_setup("X", "up", structure_state="BEAR", zone=zone, stage1_score=70,
                            target_price=120.0)
    assert not result.eligible
    assert NO_DIRECTIONAL_EDGE in result.reason_codes


def test_q1_fails_when_zone_direction_disagrees():
    zone = make_zone(direction="down", confirmed_ts=NORMAL + timedelta(minutes=10), state=STATE_TOUCHED)
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=120.0)
    assert not result.eligible
    assert NO_DIRECTIONAL_EDGE in result.reason_codes


# --- Q2: reachable entry ---

def test_q2_fails_on_invalidated_zone():
    zone = make_zone(state=STATE_INVALIDATED, invalidated_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=120.0)
    assert not result.eligible
    assert ZONE_INVALIDATED in result.reason_codes


def test_q2_fails_on_never_touched_no_confirmation():
    zone = make_zone(state=STATE_ACTIVE)  # never even touched
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=120.0)
    assert not result.eligible
    assert NO_FRESH_SETUP in result.reason_codes


def test_q2_fails_on_expired_without_confirmation():
    zone = make_zone(state=STATE_EXPIRED, touched_ts=NORMAL + timedelta(minutes=5),
                     expired_ts=NORMAL + timedelta(minutes=60))
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=120.0)
    assert not result.eligible
    assert ENTRY_TOO_EXTENDED in result.reason_codes


# --- Q3: defensible stop and target / net R:R ---

def test_q3_fails_with_no_objective_target():
    zone = make_zone(state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=None)
    assert not result.eligible
    assert RR_BELOW_MINIMUM in result.reason_codes


def test_q3_fails_below_rr_threshold():
    # entry=106 (proximal), stop=103 (distal), risk=3. target=108 -> reward=2, R:R=0.67 < 1.5.
    zone = make_zone(state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=108.0)
    assert not result.eligible
    assert RR_BELOW_MINIMUM in result.reason_codes
    assert result.net_rr == pytest.approx(2 / 3)


def test_all_three_questions_pass_eligible():
    # entry=106, stop=103, risk=3. target=115.5 -> reward=9.5, R:R>=1.5.
    zone = make_zone(state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("GOOD", "up", structure_state="BULL", zone=zone, stage1_score=70,
                            target_price=115.5)
    assert result.eligible
    assert result.reason_codes == ()
    assert result.entry_price == 106.0
    assert result.stop_price == 103.0
    assert result.net_rr >= 1.5


def test_bearish_rr_computed_correctly():
    # Bearish zone: proximal=103 (entry side), distal=106 (invalidation side).
    zone = make_zone(direction="down", proximal=103.0, distal=106.0,
                     state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    # entry=103, stop=106, risk=3. target=94 -> reward=9, R:R=3.0.
    result = evaluate_setup("BEAR1", "down", structure_state="BEAR", zone=zone, stage1_score=60,
                            target_price=94.0)
    assert result.eligible
    assert result.net_rr == pytest.approx(3.0)
    assert result.stop_price == 106.0


# --- §5.6 bearish status ---

def test_bullish_candidate_has_no_bearish_status():
    zone = make_zone(state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "up", structure_state="BULL", zone=zone, stage1_score=70, target_price=115.5)
    assert result.bearish_status is None


def test_bearish_candidate_defaults_to_research():
    zone = make_zone(direction="down", proximal=103.0, distal=106.0,
                     state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "down", structure_state="BEAR", zone=zone, stage1_score=60, target_price=94.0)
    assert result.bearish_status == BEARISH_RESEARCH


def test_bearish_candidate_promoted_only_when_all_three_conditions_verified():
    zone = make_zone(direction="down", proximal=103.0, distal=106.0,
                     state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    partial = evaluate_setup("X", "down", structure_state="BEAR", zone=zone, stage1_score=60, target_price=94.0,
                             same_day_window_verified=True, no_restriction_verified=True,
                             liquidity_verified=False)
    assert partial.bearish_status == BEARISH_RESEARCH  # one of three missing -> stays RESEARCH

    full = evaluate_setup("X", "down", structure_state="BEAR", zone=zone, stage1_score=60, target_price=94.0,
                          same_day_window_verified=True, no_restriction_verified=True,
                          liquidity_verified=True)
    assert full.bearish_status == BEARISH_EXECUTABLE_SHORT


def test_bearish_status_never_promoted_based_on_directional_score_alone():
    # A strongly eligible bearish setup must still default to RESEARCH --
    # eligibility/score never substitutes for the three verified §5.6 conditions.
    zone = make_zone(direction="down", proximal=103.0, distal=106.0,
                     state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    result = evaluate_setup("X", "down", structure_state="BEAR", zone=zone, stage1_score=90, target_price=94.0)
    assert result.eligible
    assert result.bearish_status == BEARISH_RESEARCH


def test_invalid_direction_raises():
    zone = make_zone()
    with pytest.raises(SetupInputError):
        evaluate_setup("X", "sideways", structure_state="BULL", zone=zone, stage1_score=70,
                       target_price=120.0)


# --- select_final_candidates: top 2 per direction, never pooled ---

def _eligible_eval(symbol, net_rr_target, stage1_score=60, confirmed_minutes=10):
    zone = make_zone(zone_id=symbol, state=STATE_TOUCHED,
                     confirmed_ts=NORMAL + timedelta(minutes=confirmed_minutes))
    return evaluate_setup(symbol, "up", structure_state="BULL", zone=zone,
                          stage1_score=stage1_score, target_price=net_rr_target)


def test_select_final_candidates_caps_at_two_ranked_by_rr():
    # targets chosen so net R:R differs clearly: 106 entry / 103 stop / risk=3.
    evals = [
        _eligible_eval("LOW_RR", 108.0),    # reward=2, RR=0.67 -> ineligible (below threshold)
        _eligible_eval("MED_RR", 115.5),    # reward=9.5, RR~3.17
        _eligible_eval("HIGH_RR", 124.5),   # reward=18.5, RR~6.17
        _eligible_eval("ALSO_GOOD", 118.5), # reward=12.5, RR~4.17
    ]
    selected = select_final_candidates(evals, direction="up", max_per_side=2)
    assert len(selected) == 2
    assert [e.symbol for e in selected] == ["HIGH_RR", "ALSO_GOOD"]


def test_select_final_candidates_never_pads():
    evals = [_eligible_eval("ONLY_ONE", 115.5)]
    selected = select_final_candidates(evals, direction="up", max_per_side=2)
    assert len(selected) == 1


def test_select_final_candidates_excludes_ineligible():
    bad_zone = make_zone(state=STATE_INVALIDATED, invalidated_ts=NORMAL)
    bad = evaluate_setup("BAD", "up", structure_state="BULL", zone=bad_zone, stage1_score=80,
                         target_price=120.0)
    good = _eligible_eval("GOOD", 115.5)
    selected = select_final_candidates([bad, good], direction="up", max_per_side=2)
    assert len(selected) == 1
    assert selected[0].symbol == "GOOD"


def test_select_final_candidates_never_pools_directions():
    up_eval = _eligible_eval("UPSYM", 115.5)
    down_zone = make_zone(zone_id="DOWNSYM", direction="down", proximal=103.0, distal=106.0,
                          state=STATE_TOUCHED, confirmed_ts=NORMAL + timedelta(minutes=10))
    down_eval = evaluate_setup("DOWNSYM", "down", structure_state="BEAR", zone=down_zone,
                               stage1_score=60, target_price=94.0)
    up_selected = select_final_candidates([up_eval, down_eval], direction="up", max_per_side=2)
    down_selected = select_final_candidates([up_eval, down_eval], direction="down", max_per_side=2)
    assert [e.symbol for e in up_selected] == ["UPSYM"]
    assert [e.symbol for e in down_selected] == ["DOWNSYM"]


def test_select_final_candidates_tiebreak_by_freshness_then_stage1_score():
    # Equal net R:R (same target math), differing confirmation recency.
    stale = _eligible_eval("STALE", 115.5, stage1_score=90, confirmed_minutes=5)
    fresh = _eligible_eval("FRESH", 115.5, stage1_score=50, confirmed_minutes=20)
    selected = select_final_candidates([stale, fresh], direction="up", max_per_side=2)
    assert selected[0].symbol == "FRESH"  # more recent confirmation ranks first on an R:R tie

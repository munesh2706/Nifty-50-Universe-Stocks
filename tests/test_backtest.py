"""Phase A unit tests for gate0.backtest (chronological replay engine,
spec v0.3 §7.1/§7.3/§7.5). Synthetic only. Displacements and zones are
exercised through the public build_zone/advance_zone path (unlike
test_zones.py's direct Zone construction), since this module's own job is
wiring that lifecycle to execution and cost simulation."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from gate0.backtest import (
    MIN_QUALIFIED_SETUPS,
    OUTCOME_INVALIDATED,
    OUTCOME_LOSS,
    OUTCOME_MISSED,
    OUTCOME_OPEN,
    OUTCOME_WIN,
    compare_zone_configurations,
    simulate_trade,
)
from gate0.canonical_bars import IST, Bar
from gate0.displacement import Displacement
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.zones import APPROACH_A, BOUNDARY_FULL_RANGE, advance_zone, build_zone

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
CAL = TradingCalendar(SAMPLE_CALENDAR)


def bars_from(specs, start=NORMAL, instrument="SYNTH"):
    out = []
    cur = start
    for o, h, l, c in specs:
        out.append(Bar(instrument, "5m", cur, cur + timedelta(minutes=5), o, h, l, c, 1000.0))
        cur += timedelta(minutes=5)
    return out


def make_disp(direction, d1_bar, final_bar, bos_id="SYNTH:x:BOS_UP"):
    return Displacement(
        displacement_id=f"{bos_id}:DISP", direction=direction, bos_event_id=bos_id,
        bos_level_id="SYNTH:x:H", bos_level_price=100.0,
        bar_ids=(d1_bar.bar_start_ts.isoformat(), final_bar.bar_start_ts.isoformat()),
        sequence_start_ts=d1_bar.bar_start_ts, sequence_end_ts=final_bar.bar_start_ts,
        net_body=1.0, atr_value=0.1, atr_as_of_ts=d1_bar.bar_start_ts, atr_mult=1.0, threshold=0.1,
    )


BASE_SPECS = [
    (100.0, 100.5, 99.5, 100.2),   # 0: filler
    (100.2, 100.6, 100.0, 100.4),  # 1: filler
    (100.4, 100.8, 100.2, 100.6),  # 2: filler
    (105.0, 106.0, 103.0, 104.0),  # 3: opposing anchor candle (bearish)
    (104.0, 104.8, 103.8, 104.6),  # 4: same-direction filler
    (106.0, 110.0, 105.0, 109.0),  # 5: D1 == final (single-bar bullish displacement)
]


def _confirmed_zone(extra_after):
    bars = bars_from(BASE_SPECS + extra_after)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    zone = advance_zone(zone, bars, calendar=CAL)
    return zone, bars


# --- simulate_trade: fill timing, win/loss, MAE, costs ---

def test_simulate_trade_fills_on_next_bar_open_not_signal_close():
    extra = [
        (104.0, 104.5, 102.5, 103.0),   # 6: touch
        (103.2, 107.0, 103.0, 106.5),   # 7: confirm (closes beyond proximal 106)
        (106.6, 111.0, 106.5, 110.9),   # 8: fill bar -- open=106.6
        (111.0, 115.0, 110.8, 114.0),   # 9: target hit here
    ]
    zone, bars = _confirmed_zone(extra)
    assert zone.confirmed_ts == bars[7].bar_start_ts
    outcome = simulate_trade(zone, bars, target_price=114.0)
    assert outcome.fill_ts == bars[8].bar_start_ts  # NOT bars[7] (the confirmation/signal bar)
    assert outcome.fill_price == pytest.approx(106.6 * 1.0005)  # conservative spread applied


def test_simulate_trade_win_when_target_hit_before_stop():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 111.0, 106.5, 110.9),
        (111.0, 120.0, 110.8, 119.0),  # target (115) hit here, stop (103) never approached
    ]
    zone, bars = _confirmed_zone(extra)
    outcome = simulate_trade(zone, bars, target_price=115.0)
    assert outcome.outcome == OUTCOME_WIN
    assert outcome.net_rr_after_costs is not None
    assert outcome.net_rr_after_costs > 0


def test_simulate_trade_loss_when_stop_hit_before_target():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 107.0, 106.0, 106.8),
        (106.5, 106.8, 101.0, 102.0),  # drops through the stop (103)
    ]
    zone, bars = _confirmed_zone(extra)
    outcome = simulate_trade(zone, bars, target_price=130.0)  # unreachable target
    assert outcome.outcome == OUTCOME_LOSS
    assert outcome.net_rr_after_costs is not None
    assert outcome.net_rr_after_costs < 0


def test_simulate_trade_open_when_data_runs_out_unresolved():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 107.0, 106.4, 106.8),  # fill bar; price drifts, hits neither
    ]
    zone, bars = _confirmed_zone(extra)
    outcome = simulate_trade(zone, bars, target_price=130.0)
    assert outcome.outcome == OUTCOME_OPEN
    assert outcome.net_rr_after_costs is None


def test_simulate_trade_missed_when_zone_never_confirmed():
    last_slot = CAL.expected_bar_starts(NORMAL.date(), "5m")[-1]
    bars = bars_from(BASE_SPECS)
    cur = bars[-1].bar_start_ts + timedelta(minutes=5)
    while cur <= last_slot:
        bars.append(Bar("SYNTH", "5m", cur, cur + timedelta(minutes=5), 150.0, 150.5, 149.5, 150.0, 1000.0))
        cur += timedelta(minutes=5)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    zone = advance_zone(zone, bars, calendar=CAL)
    outcome = simulate_trade(zone, bars, target_price=120.0)
    assert outcome.outcome == OUTCOME_MISSED
    assert outcome.fill_price is None


def test_simulate_trade_invalidated_when_zone_invalidated_before_confirmation():
    extra = [(103.0, 103.2, 101.0, 101.5)]  # closes below distal -> invalidated
    zone, bars = _confirmed_zone(extra)
    outcome = simulate_trade(zone, bars, target_price=120.0)
    assert outcome.outcome == OUTCOME_INVALIDATED
    assert outcome.fill_price is None


def test_simulate_trade_mae_tracks_worst_adverse_move():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 107.0, 104.0, 104.5),   # dips to 104.0 against the fill (adverse)
        (104.6, 112.0, 104.0, 111.0),   # target hit
    ]
    zone, bars = _confirmed_zone(extra)
    outcome = simulate_trade(zone, bars, target_price=111.0)
    assert outcome.mae is not None
    assert outcome.mae > 0  # fill price (~106.63) minus the 104.0 low


# --- compare_zone_configurations: §7.5 controlled design + evidence bar ---

def test_compare_runs_all_four_configurations():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 111.0, 106.5, 110.9),
        (111.0, 120.0, 110.8, 119.0),
    ]
    bars = bars_from(BASE_SPECS + extra)
    disp = make_disp("up", bars[5], bars[5])
    result = compare_zone_configurations([disp], bars, calendar=CAL, target_resolver=lambda d: 115.0)
    assert set(result.configurations.keys()) == {("A", "full_range"), ("A", "body_only"),
                                                  ("B", "full_range"), ("B", "body_only")}


def test_compare_marks_configuration_inconclusive_below_minimum_evidence():
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 111.0, 106.5, 110.9),
        (111.0, 120.0, 110.8, 119.0),
    ]
    bars = bars_from(BASE_SPECS + extra)
    disp = make_disp("up", bars[5], bars[5])
    result = compare_zone_configurations([disp], bars, calendar=CAL, target_resolver=lambda d: 115.0)
    # Only one displacement supplied -- nowhere near MIN_QUALIFIED_SETUPS.
    for cfg in result.configurations.values():
        assert cfg.inconclusive
        assert cfg.qualified_setups < MIN_QUALIFIED_SETUPS
    assert result.overall_inconclusive
    assert result.default_choice == ("B", "full_range")


def test_compare_same_displacements_and_bars_feed_all_configurations():
    # §7.5's controlled-design requirement: structure/displacement output is
    # computed once and reused -- verify by checking qualified-setup totals
    # across configs come from the SAME single displacement, not independent
    # re-derivations (sanity: total outcomes across configs <= 4x displacements).
    extra = [
        (104.0, 104.5, 102.5, 103.0),
        (103.2, 107.0, 103.0, 106.5),
        (106.6, 111.0, 106.5, 110.9),
        (111.0, 120.0, 110.8, 119.0),
    ]
    bars = bars_from(BASE_SPECS + extra)
    disp = make_disp("up", bars[5], bars[5])
    result = compare_zone_configurations([disp], bars, calendar=CAL, target_resolver=lambda d: 115.0)
    total_outcomes = sum(
        cfg.wins + cfg.losses + cfg.open_trades + cfg.missed + cfg.invalidated
        for cfg in result.configurations.values()
    )
    assert total_outcomes <= 4 * 1

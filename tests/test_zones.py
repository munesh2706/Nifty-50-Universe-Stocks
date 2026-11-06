"""Phase A unit tests for gate0.zones (Approach A/B zone models, spec v0.3
§5.3-§5.4). Synthetic only. Displacement objects are constructed directly
(not via detect_displacement) to isolate zone-model behavior."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.displacement import Displacement
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.zones import (
    APPROACH_A,
    APPROACH_B,
    BOUNDARY_BODY_ONLY,
    BOUNDARY_FULL_RANGE,
    STATE_ACTIVE,
    STATE_EXPIRED,
    STATE_INVALIDATED,
    STATE_TOUCHED,
    ZoneInputError,
    advance_zone,
    build_zone,
)

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
EARLY = datetime(2026, 11, 6, 9, 15, tzinfo=IST)
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


# idx: 0        1         2         3(anchor,opp)  4(same dir)  5(D1, final)
SPECS = [
    (100.0, 100.5, 99.5, 100.2),   # 0: filler, bullish
    (100.2, 100.6, 100.0, 100.4),  # 1: filler, bullish
    (100.4, 100.8, 100.2, 100.6),  # 2: filler, bullish
    (105.0, 106.0, 103.0, 104.0),  # 3: nearest opposing (bearish) candle before D1
    (104.0, 104.8, 103.8, 104.6),  # 4: same-direction (bullish), closer to D1 than idx3
    (106.0, 110.0, 105.0, 109.0),  # 5: D1 == final (single-bar bullish displacement)
]


def make_bars(extra_after=()):
    return bars_from(list(SPECS) + list(extra_after))


# --- build_zone: Approach A anchor selection and boundary types ---

def test_approach_a_selects_nearest_opposing_candle_full_range():
    bars = make_bars()
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is not None
    assert zone.anchor_bar_id == bars[3].bar_start_ts.isoformat()  # idx3, not idx4 (same direction, skipped)
    assert zone.proximal == 106.0  # anchor's high
    assert zone.distal == 103.0    # anchor's low
    assert zone.state == STATE_ACTIVE


def test_approach_a_body_only_boundary():
    bars = make_bars()
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_BODY_ONLY)
    assert zone is not None
    assert zone.proximal == 105.0  # max(open, close) of the anchor (bearish: open > close)
    assert zone.distal == 104.0    # min(open, close)


def test_approach_a_no_opposing_candle_returns_none():
    # Replace idx3 with a same-direction candle too -- no opposing candle in
    # the whole 5-bar lookback -> Approach A has no zone (NO_ANCHOR_CANDLE).
    specs = list(SPECS)
    specs[3] = (100.4, 100.9, 100.3, 100.7)  # now bullish, not opposing
    bars = bars_from(specs)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is None


def test_approach_a_lookback_capped_at_five_bars():
    # An opposing candle exists, but 6 bars before D1 (outside the 5-bar cap).
    far_opposite = (105.0, 106.0, 103.0, 104.0)  # bearish, but idx0 here with D1 at idx6
    specs = [far_opposite] + [(100.0 + i * 0.1, 100.5 + i * 0.1, 99.5 + i * 0.1, 100.2 + i * 0.1) for i in range(5)] \
        + [(106.0, 110.0, 105.0, 109.0)]
    bars = bars_from(specs)
    d1 = bars[6]
    disp = make_disp("up", d1, d1)
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is None  # the only opposing candle is outside the 5-bar lookback


# --- build_zone: Approach B (no anchor search, uses D1 directly) ---

def test_approach_b_uses_d1_directly_no_anchor():
    bars = make_bars()
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_B, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is not None
    assert zone.anchor_bar_id is None
    assert zone.proximal == 110.0  # D1's own high
    assert zone.distal == 105.0    # D1's own low


def test_approach_b_never_returns_none_even_with_no_opposing_candle():
    specs = list(SPECS)
    specs[3] = (100.4, 100.9, 100.3, 100.7)  # same fixture that defeats Approach A
    bars = bars_from(specs)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_B, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is not None


def test_zones_record_which_approach_produced_them():
    bars = make_bars()
    disp = make_disp("up", bars[5], bars[5])
    za = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    zb = build_zone(disp, bars, calendar=CAL, approach=APPROACH_B, boundary_type=BOUNDARY_FULL_RANGE)
    assert za.approach == "A" and zb.approach == "B"
    assert za.zone_id != zb.zone_id


# --- advance_zone: touch, confirmation, invalidation, expiry ---

def test_advance_zone_touch_then_confirm():
    # After creation: bar 6 dips into the zone (touch), bar 7 closes back
    # beyond proximal in the displacement direction (confirmation).
    extra = [
        (104.0, 104.5, 102.5, 103.0),  # 6: touches [103,106] range, closes inside (no confirm yet)
        (103.2, 107.0, 103.0, 106.5),  # 7: closes beyond proximal (106) in the up direction -> confirm
    ]
    bars = make_bars(extra)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    advanced = advance_zone(zone, bars, calendar=CAL)
    assert advanced.touched_ts == bars[6].bar_start_ts
    assert advanced.confirmed_ts == bars[7].bar_start_ts


def test_advance_zone_invalidated_beyond_distal():
    extra = [
        (103.0, 103.2, 101.0, 101.5),  # 6: closes below distal (103) -> invalidated
    ]
    bars = make_bars(extra)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    advanced = advance_zone(zone, bars, calendar=CAL)
    assert advanced.state == STATE_INVALIDATED
    assert advanced.invalidated_ts == bars[6].bar_start_ts
    assert advanced.confirmed_ts is None


def test_advance_zone_expires_at_real_session_close_without_touch():
    # Pad with neutral bars (never touching [103,106]) all the way through
    # the calendar's actual last 5m slot of the session.
    last_slot = CAL.expected_bar_starts(NORMAL.date(), "5m")[-1]
    bars = make_bars()
    cur = bars[-1].bar_start_ts + timedelta(minutes=5)
    while cur <= last_slot:
        bars.append(Bar("SYNTH", "5m", cur, cur + timedelta(minutes=5), 150.0, 150.5, 149.5, 150.0, 1000.0))
        cur += timedelta(minutes=5)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    advanced = advance_zone(zone, bars, calendar=CAL)
    assert advanced.state == STATE_EXPIRED
    assert advanced.touched_ts is None
    assert advanced.confirmed_ts is None


def test_advance_zone_stays_active_mid_session_pending_more_data():
    # Only a few bars supplied after creation, nowhere near the session's
    # real close and no gap/next-segment bar proving the segment ended --
    # must remain ACTIVE, not prematurely expire.
    extra = [(150.0, 150.5, 149.5, 150.0)]  # neutral, no touch
    bars = make_bars(extra)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    advanced = advance_zone(zone, bars, calendar=CAL)
    assert advanced.state == STATE_ACTIVE


def test_advance_zone_expires_on_gap_rather_than_touching_across_it():
    # A bar that WOULD touch the zone appears only after a session/gap
    # boundary (next day). Rule 10: it must not touch/confirm/invalidate
    # across that boundary -- the zone instead expires at the original
    # segment's end, proven by the later (next-session) bar's presence.
    bars = make_bars()
    next_session = bars_from([(103.0, 104.0, 102.0, 103.5)], start=EARLY)  # would touch [103,106]
    all_bars = bars + next_session
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    advanced = advance_zone(zone, all_bars, calendar=CAL)
    assert advanced.state == STATE_EXPIRED
    assert advanced.touched_ts is None


def test_advance_zone_terminal_state_is_idempotent():
    extra = [(103.0, 103.2, 101.0, 101.5)]  # invalidates
    bars = make_bars(extra)
    disp = make_disp("up", bars[5], bars[5])
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    once = advance_zone(zone, bars, calendar=CAL)
    twice = advance_zone(once, bars, calendar=CAL)
    assert once == twice


def test_bearish_zone_mirrors_direction():
    # Bearish displacement: anchor must be a bullish (opposing) candle;
    # proximal/distal flip sides.
    specs = [
        (100.0, 100.5, 99.5, 100.2),
        (100.2, 100.6, 100.0, 100.4),
        (100.4, 100.8, 100.2, 100.6),
        (104.0, 106.0, 103.0, 105.0),  # bullish anchor (close > open)
        (104.6, 104.8, 103.8, 104.0),  # same-direction (bearish), closer to D1
        (109.0, 110.0, 105.0, 106.0),  # D1: bearish displacement (close < open)
    ]
    bars = bars_from(specs)
    disp = make_disp("down", bars[5], bars[5], bos_id="SYNTH:x:BOS_DOWN")
    zone = build_zone(disp, bars, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)
    assert zone is not None
    assert zone.anchor_bar_id == bars[3].bar_start_ts.isoformat()
    assert zone.proximal == 103.0  # bearish: proximal = anchor's low
    assert zone.distal == 106.0    # distal = anchor's high


def test_build_zone_rejects_non_5m_bars():
    bars = make_bars()
    bad = [Bar("SYNTH", "15m", NORMAL, NORMAL + timedelta(minutes=15), 1, 2, 0.5, 1, 100)]
    disp = make_disp("up", bars[5], bars[5])
    with pytest.raises(ZoneInputError):
        build_zone(disp, bad, calendar=CAL, approach=APPROACH_A, boundary_type=BOUNDARY_FULL_RANGE)

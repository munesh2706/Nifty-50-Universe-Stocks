"""Approach A / Approach B zone models and lifecycle (Gate 0 harness, Phase A)
— spec v0.3 §5.3-§5.4.

Pure, repository-only. No network/provider/credentials. Consumes a validated
completed 5m `Bar` series for ONE instrument, an explicit `TradingCalendar`,
and a `Displacement` from `displacement.py` (which itself was derived from an
accepted `StructureResult`).

Scope: §5.3 Approach A (minimal order-block: 5-bar lookback, nearest-opposing-
candle anchor, full-range/body-only boundary choice) and §5.4 Approach B
(displacement-origin pullback zone, no anchor search) — both sharing the
identical touch/confirmation/invalidation/expiry mechanics (§5.3 rules 5-10),
so the §7.5 comparison isolates only the zone-selection step. Approach A and
Approach B are never treated as equivalent; every zone records which produced
it. No nested zones, no repeated-touch classification, no additional
liquidity subsystems (those are explicitly out of scope for v1, per §5.3).

No look-ahead: `advance_zone` only consumes bars strictly at or after zone
creation, within the zone's own creation session segment (§5.3 rule 10) —
a zone cannot be touched, confirmed or invalidated by a bar on the far side
of a session/gap boundary; such a bar instead triggers expiry.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from gate0.canonical_bars import Bar
from gate0.displacement import Displacement
from gate0.nse_calendar import TradingCalendar
from gate0.structure import _segment

APPROACH_A = "A"
APPROACH_B = "B"
BOUNDARY_FULL_RANGE = "full_range"
BOUNDARY_BODY_ONLY = "body_only"

STATE_ACTIVE = "ACTIVE"
STATE_TOUCHED = "TOUCHED"
STATE_INVALIDATED = "INVALIDATED"
STATE_EXPIRED = "EXPIRED"

NO_ANCHOR_CANDLE = "NO_ANCHOR_CANDLE"
MAX_ANCHOR_LOOKBACK = 5  # §5.3 rule 1


class ZoneInputError(ValueError):
    """Fail-closed: malformed input to zone construction/advancement."""


@dataclass(frozen=True)
class Zone:
    zone_id: str
    approach: str  # "A" | "B"
    direction: str  # "up" | "down"
    boundary_type: str  # "full_range" | "body_only"
    proximal: float
    distal: float
    anchor_bar_id: str | None  # the anchor candle's bar_start isoformat (A only; None for B)
    displacement_id: str
    created_ts: datetime  # the bar_end of the displacement's own final (confirming) bar
    state: str = STATE_ACTIVE
    touched_ts: datetime | None = None
    confirmed_ts: datetime | None = None  # the entry-trigger bar's bar_start_ts, if any
    invalidated_ts: datetime | None = None
    expired_ts: datetime | None = None


def _bar_id(b: Bar) -> str:
    return b.bar_start_ts.isoformat()


def _find_creation_segment(bars_5m: list[Bar], calendar: TradingCalendar, d1_ts: datetime) -> list[Bar]:
    for seg in _segment(bars_5m, calendar, "5m"):
        if seg[0].bar_start_ts <= d1_ts <= seg[-1].bar_start_ts:
            return seg
    raise ZoneInputError("displacement's D1 bar is not within any session segment of the supplied bars")


def _boundary(bar: Bar, direction: str, boundary_type: str) -> tuple[float, float]:
    """Returns (proximal, distal) for `bar` as the zone source candle."""
    if boundary_type == BOUNDARY_FULL_RANGE:
        hi, lo = bar.high, bar.low
    elif boundary_type == BOUNDARY_BODY_ONLY:
        hi, lo = max(bar.open, bar.close), min(bar.open, bar.close)
    else:
        raise ZoneInputError(f"unknown boundary_type: {boundary_type}")
    return (hi, lo) if direction == "up" else (lo, hi)


def build_zone(
    displacement: Displacement,
    bars_5m: list[Bar],
    *,
    calendar: TradingCalendar,
    approach: str,
    boundary_type: str = BOUNDARY_FULL_RANGE,
) -> Zone | None:
    """§5.3 (Approach A) / §5.4 (Approach B): builds the zone for one
    displacement. Returns None for Approach A with no valid anchor within the
    5-bar lookback (reason code `NO_ANCHOR_CANDLE`, §5.3 rule 3) — Approach B
    never returns None (D1 always exists whenever `displacement` exists).
    """
    if approach not in (APPROACH_A, APPROACH_B):
        raise ZoneInputError(f"unknown approach: {approach}")
    if boundary_type not in (BOUNDARY_FULL_RANGE, BOUNDARY_BODY_ONLY):
        raise ZoneInputError(f"unknown boundary_type: {boundary_type}")
    if any(b.timeframe != "5m" for b in bars_5m):
        raise ZoneInputError("zones.py operates on 5m bars only")

    bars_by_ts = {b.bar_start_ts: b for b in bars_5m}
    direction = displacement.direction
    d1_ts = displacement.sequence_start_ts
    if d1_ts not in bars_by_ts or displacement.sequence_end_ts not in bars_by_ts:
        raise ZoneInputError("displacement's bars are not within the supplied bar series")

    seg = _find_creation_segment(bars_5m, calendar, d1_ts)
    d1_idx = next(i for i, b in enumerate(seg) if b.bar_start_ts == d1_ts)
    final_bar = bars_by_ts[displacement.sequence_end_ts]
    created_ts = final_bar.bar_end_ts

    if approach == APPROACH_A:
        lookback = seg[max(0, d1_idx - MAX_ANCHOR_LOOKBACK):d1_idx]  # within same segment, <= 5 bars
        anchor: Bar | None = None
        for cand in reversed(lookback):  # scan backward from the bar immediately before D1 -> nearest first
            is_opposite = (cand.close < cand.open) if direction == "up" else (cand.close > cand.open)
            if is_opposite:
                anchor = cand
                break
        if anchor is None:
            return None  # NO_ANCHOR_CANDLE
        source_bar, anchor_bar_id = anchor, _bar_id(anchor)
    else:
        source_bar, anchor_bar_id = bars_by_ts[d1_ts], None

    proximal, distal = _boundary(source_bar, direction, boundary_type)
    zone_id = f"{displacement.displacement_id}:Z{approach}:{boundary_type}"
    return Zone(
        zone_id=zone_id, approach=approach, direction=direction, boundary_type=boundary_type,
        proximal=proximal, distal=distal, anchor_bar_id=anchor_bar_id,
        displacement_id=displacement.displacement_id, created_ts=created_ts,
    )


def advance_zone(zone: Zone, bars_5m: list[Bar], *, calendar: TradingCalendar) -> Zone:
    """§5.3 rules 5-10: applies the shared touch/confirmation/invalidation/
    expiry mechanics, using only bars at/after `zone.created_ts` within the
    zone's own creation session segment. Pure: returns a new `Zone`, never
    mutates. A zone already in a terminal state (`INVALIDATED`/`EXPIRED`) is
    returned unchanged.
    """
    if zone.state in (STATE_INVALIDATED, STATE_EXPIRED):
        return zone
    if any(b.timeframe != "5m" for b in bars_5m):
        raise ZoneInputError("zones.py operates on 5m bars only")

    # Locate the zone's own creation segment: the segment containing the bar
    # whose bar_end_ts == created_ts (the displacement's final/confirming
    # bar) -- or, if that bar is not in the supplied window, the segment
    # containing the first bar at/after created_ts (same segment, since a
    # new segment only starts on a session/gap boundary, never mid-touch).
    seg = None
    for candidate in _segment(bars_5m, calendar, "5m"):
        if any(b.bar_end_ts == zone.created_ts or b.bar_start_ts == zone.created_ts for b in candidate):
            seg = candidate
            break
    if seg is None:
        return zone  # no bars yet in this zone's segment -> nothing to advance

    after = [b for b in seg if b.bar_start_ts >= zone.created_ts]

    state, touched_ts, confirmed_ts = zone.state, zone.touched_ts, zone.confirmed_ts
    invalidated_ts, expired_ts = zone.invalidated_ts, zone.expired_ts
    direction = zone.direction
    lo_b, hi_b = min(zone.distal, zone.proximal), max(zone.distal, zone.proximal)

    for b in after:
        beyond_distal = (b.close < zone.distal) if direction == "up" else (b.close > zone.distal)
        if beyond_distal:
            state, invalidated_ts = STATE_INVALIDATED, b.bar_start_ts
            break
        if state == STATE_ACTIVE:
            intersects = not (b.low > hi_b or b.high < lo_b)
            if intersects:
                state, touched_ts = STATE_TOUCHED, b.bar_start_ts
            continue
        if state == STATE_TOUCHED and confirmed_ts is None:
            closes_in_direction = (b.close > b.open) if direction == "up" else (b.close < b.open)
            beyond_proximal = (b.close > zone.proximal) if direction == "up" else (b.close < zone.proximal)
            if closes_in_direction and beyond_proximal:
                confirmed_ts = b.bar_start_ts
                break  # §5.3 rule 6: the entry trigger bar -- the zone's job is done

    if state in (STATE_ACTIVE, STATE_TOUCHED) and confirmed_ts is None:
        # §5.3 rule 8: expire only once the zone's own creation segment has
        # *actually* ended -- either proven by a later bar in the supplied
        # data (a real gap/next-session bar, so this segment's run is
        # genuinely over), or because this segment's last bar is the
        # calendar's own last expected 5m slot of the session (session
        # close reached even with no further data supplied). Simply running
        # out of supplied bars mid-segment is "not yet known", not expired —
        # a live/intraday caller passes a growing bar window, and the real
        # session may still be in progress.
        has_bar_after_segment = any(b.bar_start_ts > seg[-1].bar_start_ts for b in bars_5m)
        session_date = seg[0].bar_start_ts.date()
        is_session_close = seg[-1].bar_start_ts == calendar.expected_bar_starts(session_date, "5m")[-1]
        if has_bar_after_segment or is_session_close:
            state, expired_ts = STATE_EXPIRED, seg[-1].bar_end_ts

    return replace(zone, state=state, touched_ts=touched_ts, confirmed_ts=confirmed_ts,
                    invalidated_ts=invalidated_ts, expired_ts=expired_ts)

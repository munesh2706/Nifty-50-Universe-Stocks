"""Deterministic 5m market structure (Gate 0 harness, Phase A) — spec v0.2 §7.1-7.3.

Pure, repository-only. No network/provider/credentials. Consumes a validated
series of completed 5m `Bar`s for ONE instrument plus an explicit
`TradingCalendar`, and produces a deterministic, ordered list of structure
events, the confirmed swing pivots, and equal-extreme liquidity pools.

Scope (comms/claude/017+018, 024): §7.1 swing pivots, §7.1 equal-extreme pools,
§7.2 BOS, §7.3 CHoCH state machine (protection_pending; the two determinism
events). §7.4-7.10 and sweep detection are OUT of scope.

Determinism guarantees:
- Fail-closed validation: empty input, invalid series, non-5m bars, non-finite/
  non-positive tick, empty tick source, invalid buffer, and off-grid OHLC all
  raise (C3).
- Calendar-based session segmentation (C4): every bar must be an expected slot of
  the supplied TradingCalendar; segments split on session/overnight boundaries and
  missing expected slots; no pivot window/pool/state bridges a boundary; the state
  machine resets to NEUTRAL per segment. Missing bars are never fabricated.
- Consumed-level tracking (C1): a BOS/CHoCH level is emitted once; a close that
  merely stays beyond the same pivot does not re-emit.
- Non-chainable tick-grid pool grouping (C2): a pool's full price range is within
  one tick; prices compared as integers (explicit tick_size + source; no float
  epsilon).
- No look-ahead: a pivot/pool is usable only after its right-side confirmation bar
  has closed.
- Stable event order: (bar_start_ts, event_priority, level_price_ticks, level_id).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from gate0.canonical_bars import IST, Bar, validate_series
from gate0.nse_calendar import TradingCalendar

# Event types
BOS_UP = "BOS_UP"
BOS_DOWN = "BOS_DOWN"
CHOCH_UP = "CHOCH_UP"
CHOCH_DOWN = "CHOCH_DOWN"
AMBIGUOUS_DOUBLE_BREAK = "STRUCTURE_AMBIGUOUS_DOUBLE_BREAK"
PROTECTION_PENDING = "STRUCTURE_PROTECTION_PENDING"

_EVENT_PRIORITY = {
    BOS_UP: 10, BOS_DOWN: 10, CHOCH_UP: 10, CHOCH_DOWN: 10,
    AMBIGUOUS_DOUBLE_BREAK: 10,
    PROTECTION_PENDING: 20,  # emitted after the CHoCH on the same bar
}


@dataclass(frozen=True)
class Pivot:
    kind: str  # "high" | "low"
    price: float
    pivot_time: datetime
    confirmation_time: datetime
    pivot_id: str


@dataclass(frozen=True)
class Pool:
    kind: str  # "high" | "low"
    reference_price: float
    member_ids: tuple[str, ...]
    confirmation_time: datetime
    tick_size: float
    tick_size_source: str


@dataclass(frozen=True)
class StructureEvent:
    type: str
    bar_start_ts: datetime
    direction: str  # "up" | "down" | "none"
    level_price: float | None
    level_id: str | None
    second_level_id: str | None = None  # C5: both IDs for the ambiguous event


@dataclass(frozen=True)
class StructureResult:
    events: list[StructureEvent] = field(default_factory=list)
    pivots: list[Pivot] = field(default_factory=list)
    pools: list[Pool] = field(default_factory=list)
    # R1 (review 040): the bar_start_ts each 5m structure segment began at, in
    # order. The state machine resets to NEUTRAL at every one of these points
    # (including a segment with zero events) -- a consumer deriving "current
    # state as of some later timestamp" must reset at the latest segment_start
    # <= that timestamp, not infer resets from an unrelated timeframe's own
    # segmentation.
    segment_starts: tuple[datetime, ...] = field(default_factory=tuple)


def _ticks(price: float, tick: float) -> int:
    return int((Decimal(str(price)) / Decimal(str(tick))).to_integral_value())


def _on_grid(price: float, tick: float) -> bool:
    try:
        return (Decimal(str(price)) % Decimal(str(tick))) == 0
    except Exception:
        return False


def _ist_date(b: Bar):
    return b.bar_start_ts.astimezone(IST).date()


def _segment(bars: list[Bar], calendar: TradingCalendar, timeframe: str) -> list[list[Bar]]:
    """Calendar-based segmentation (C4).

    Every bar must be an expected slot for its date/timeframe (else ValueError).
    A new segment starts on a date (session/overnight) change or a missing
    expected slot (the bar is not the immediate successor of the previous one).
    """
    segments: list[list[Bar]] = []
    cur: list[Bar] = []
    for b in bars:
        d = _ist_date(b)
        slots = calendar.expected_bar_starts(d, timeframe)
        slot_set = {s for s in slots}
        start_ist = b.bar_start_ts.astimezone(IST)
        if start_ist not in slot_set:
            raise ValueError(f"bar {b.bar_start_ts.isoformat()} is not an expected {timeframe} session slot")
        if cur:
            prev = cur[-1]
            same_day = _ist_date(prev) == d
            contiguous = b.bar_start_ts == prev.bar_end_ts
            if not (same_day and contiguous):
                segments.append(cur)
                cur = []
        cur.append(b)
    if cur:
        segments.append(cur)
    return segments


def _swings(seg: list[Bar], instrument: str) -> list[Pivot]:
    out: list[Pivot] = []
    for i in range(2, len(seg) - 2):
        hi, lo = seg[i].high, seg[i].low
        others = (seg[i - 2], seg[i - 1], seg[i + 1], seg[i + 2])
        if all(hi > o.high for o in others):
            out.append(Pivot("high", hi, seg[i].bar_start_ts, seg[i + 2].bar_end_ts,
                             f"{instrument}:{seg[i].bar_start_ts.isoformat()}:H"))
        if all(lo < o.low for o in others):
            out.append(Pivot("low", lo, seg[i].bar_start_ts, seg[i + 2].bar_end_ts,
                             f"{instrument}:{seg[i].bar_start_ts.isoformat()}:L"))
    return out


def _confirmed_before(pivots: list[Pivot], kind: str, before_ts: datetime) -> Pivot | None:
    best: Pivot | None = None
    for p in pivots:
        if p.kind == kind and p.confirmation_time < before_ts:
            if best is None or p.pivot_time > best.pivot_time:
                best = p
    return best


def _pools(seg: list[Bar], instrument: str, tick: float, source: str) -> list[Pool]:
    """Equal-extreme pools with non-chainable tick-grid grouping (C2)."""
    pools: list[Pool] = []
    for kind, pick in (("high", lambda b: b.high), ("low", lambda b: b.low)):
        candidates: list[tuple[int, float, datetime, str]] = []  # (ticks, price, conf, id)
        for i in range(2, len(seg) - 2):
            v = pick(seg[i])
            vals = [pick(n) for n in (seg[i - 2], seg[i - 1], seg[i + 1], seg[i + 2])]
            ok = (all(v >= x for x in vals) and any(v > x for x in vals)) if kind == "high" \
                else (all(v <= x for x in vals) and any(v < x for x in vals))
            if ok:
                cid = f"{instrument}:{seg[i].bar_start_ts.isoformat()}:{'EH' if kind == 'high' else 'EL'}"
                candidates.append((_ticks(v, tick), v, seg[i + 2].bar_end_ts, cid))
        candidates.sort(key=lambda c: (c[0], c[2], c[3]))
        cluster: list[tuple[int, float, datetime, str]] = []
        for cand in candidates:
            # non-chainable: the whole cluster's tick span must stay within 1 tick.
            if cluster and (cand[0] - cluster[0][0]) > 1:
                pools.extend(_make_pool(kind, cluster, tick, source))
                cluster = []
            cluster.append(cand)
        pools.extend(_make_pool(kind, cluster, tick, source))
    return pools


def _make_pool(kind, cluster, tick, source) -> list[Pool]:
    if len(cluster) < 2:
        return []
    # C8: median computed in integer ticks with a documented deterministic rule:
    # odd count -> middle tick; even count -> arithmetic mean of the two middle
    # ticks, rounded HALF UP (toward the higher tick). No float round().
    tks = sorted(c[0] for c in cluster)
    n = len(tks)
    if n % 2:
        med_tick = tks[n // 2]
    else:
        med_tick = (tks[n // 2 - 1] + tks[n // 2] + 1) // 2  # (a+b)/2 rounded half up
    reference_price = float(Decimal(med_tick) * Decimal(str(tick)))
    member_ids = tuple(sorted(c[3] for c in cluster))
    confirmation_time = max(c[2] for c in cluster)
    return [Pool(kind, reference_price, member_ids, confirmation_time, tick, source)]


def _run_state_machine(seg: list[Bar], pivots: list[Pivot], tick: float, buffer_ticks: int) -> list[StructureEvent]:
    buffer = buffer_ticks * tick
    state = "NEUTRAL"
    protected_low: Pivot | None = None
    protected_high: Pivot | None = None
    # NOTE: `protection_pending` is a DEFENSIVE INVARIANT / state guard, not an
    # ordinarily reachable transition: under the agreed "latest-confirmed-swing"
    # semantics within a segment, establishing a directional state always leaves a
    # confirmed opposite pivot behind, so the repopulation branch does not return
    # null in normal data. It is retained per the agreed §7.3 contract.
    protection_pending = False
    # C1 + C7: consumption is event-scoped. A pivot consumed as a BOS level must
    # still be usable later as a CHoCH protected level (and vice versa).
    consumed_bos: set[str] = set()
    consumed_choch: set[str] = set()
    events: list[StructureEvent] = []

    for b in seg:
        ts, close = b.bar_start_ts, b.close
        sh = _confirmed_before(pivots, "high", ts)
        sl = _confirmed_before(pivots, "low", ts)
        broke_high = sh is not None and close > sh.price + buffer
        broke_low = sl is not None and close < sl.price - buffer

        if state == "NEUTRAL":
            if broke_high and broke_low:
                events.append(StructureEvent(AMBIGUOUS_DOUBLE_BREAK, ts, "none", sh.price, sh.pivot_id, sl.pivot_id))
            elif broke_high and sl is not None and sh.pivot_id not in consumed_bos:
                events.append(StructureEvent(BOS_UP, ts, "up", sh.price, sh.pivot_id))
                consumed_bos.add(sh.pivot_id)
                state, protected_low, protection_pending = "BULL", sl, False
            elif broke_low and sh is not None and sl.pivot_id not in consumed_bos:
                events.append(StructureEvent(BOS_DOWN, ts, "down", sl.price, sl.pivot_id))
                consumed_bos.add(sl.pivot_id)
                state, protected_high, protection_pending = "BEAR", sh, False

        elif state == "BULL":
            if (not protection_pending) and protected_low is not None \
                    and close < protected_low.price - buffer and protected_low.pivot_id not in consumed_choch:
                events.append(StructureEvent(CHOCH_DOWN, ts, "down", protected_low.price, protected_low.pivot_id))
                consumed_choch.add(protected_low.pivot_id)
                state = "BEAR"
                newsh = _confirmed_before(pivots, "high", ts)
                if newsh is None:
                    protected_high, protection_pending = None, True
                    events.append(StructureEvent(PROTECTION_PENDING, ts, "down", None, None))
                else:
                    protected_high, protection_pending = newsh, False
            elif broke_high and sh.pivot_id not in consumed_bos:
                events.append(StructureEvent(BOS_UP, ts, "up", sh.price, sh.pivot_id))
                consumed_bos.add(sh.pivot_id)
                newsl = _confirmed_before(pivots, "low", ts)
                protected_low, protection_pending = newsl, newsl is None

        elif state == "BEAR":
            if (not protection_pending) and protected_high is not None \
                    and close > protected_high.price + buffer and protected_high.pivot_id not in consumed_choch:
                events.append(StructureEvent(CHOCH_UP, ts, "up", protected_high.price, protected_high.pivot_id))
                consumed_choch.add(protected_high.pivot_id)
                state = "BULL"
                newsl = _confirmed_before(pivots, "low", ts)
                if newsl is None:
                    protected_low, protection_pending = None, True
                    events.append(StructureEvent(PROTECTION_PENDING, ts, "up", None, None))
                else:
                    protected_low, protection_pending = newsl, False
            elif broke_low and sl.pivot_id not in consumed_bos:
                events.append(StructureEvent(BOS_DOWN, ts, "down", sl.price, sl.pivot_id))
                consumed_bos.add(sl.pivot_id)
                newsh = _confirmed_before(pivots, "high", ts)
                protected_high, protection_pending = newsh, newsh is None

    return events


def detect_structure(
    bars: list[Bar],
    *,
    calendar: TradingCalendar,
    tick_size: float,
    tick_size_source: str,
    buffer_ticks: int = 0,
) -> StructureResult:
    """Detect §7.1-7.3 structure on a validated completed-5m series (one instrument).

    Requires an explicit TradingCalendar (C4). Fail-closed on all invalid input.
    """
    if not bars:
        raise ValueError("empty input: structure detection requires >= 1 completed 5m bar")
    if not isinstance(calendar, TradingCalendar):
        raise ValueError("an explicit TradingCalendar is required")
    if not (isinstance(tick_size, (int, float)) and math.isfinite(tick_size) and tick_size > 0):
        raise ValueError("tick_size must be a finite positive number")
    if not (isinstance(tick_size_source, str) and tick_size_source.strip()):
        raise ValueError("tick_size_source must be a non-empty provenance string")
    if isinstance(buffer_ticks, bool) or not isinstance(buffer_ticks, int) or buffer_ticks < 0:
        raise ValueError("buffer_ticks must be a non-negative integer")

    problems = validate_series(bars, require_complete=True)
    if problems:
        raise ValueError(f"invalid bar series (fail-closed): {problems[:5]}")
    if any(b.timeframe != "5m" for b in bars):
        raise ValueError("structure operates on 5m bars only")
    for b in bars:  # C3: reject off-grid OHLC deterministically
        if not all(_on_grid(v, tick_size) for v in (b.open, b.high, b.low, b.close)):
            raise ValueError(f"off-grid OHLC at {b.bar_start_ts.isoformat()} for tick {tick_size}")

    instrument = bars[0].instrument_id
    all_events: list[StructureEvent] = []
    all_pivots: list[Pivot] = []
    all_pools: list[Pool] = []
    segment_starts: list[datetime] = []
    for seg in _segment(bars, calendar, "5m"):
        segment_starts.append(seg[0].bar_start_ts)
        pivots = _swings(seg, instrument)
        all_pivots.extend(pivots)
        all_pools.extend(_pools(seg, instrument, tick_size, tick_size_source))
        all_events.extend(_run_state_machine(seg, pivots, tick_size, buffer_ticks))

    all_events.sort(key=lambda e: (
        e.bar_start_ts,
        _EVENT_PRIORITY.get(e.type, 99),
        _ticks(e.level_price, tick_size) if e.level_price is not None else -1,
        e.level_id or "",
    ))
    return StructureResult(events=all_events, pivots=all_pivots, pools=all_pools,
                            segment_starts=tuple(segment_starts))

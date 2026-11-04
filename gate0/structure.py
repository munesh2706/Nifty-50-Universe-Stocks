"""Deterministic 5m market structure (Gate 0 harness, Phase A) — spec v0.2 §7.1-7.3.

Pure, repository-only. No network/provider/credentials. Consumes a validated
series of completed 5m `Bar`s for ONE instrument and produces a deterministic,
ordered list of structure events, plus the confirmed swing pivots and
equal-extreme liquidity pools.

Scope (comms/claude/017 + 018): §7.1 swing pivots, §7.1 equal-extreme pools,
§7.2 BOS, §7.3 CHoCH state machine (protection_pending; the two determinism
events). §7.4-7.10 and sweep *detection* are OUT of scope.

Determinism guarantees:
- Fail-closed validation; empty input raises.
- Session/gap segmentation by contiguity (a bar's start must equal the previous
  bar's end); no pivot window, pool or state bridges a segment boundary; the
  state machine resets to NEUTRAL at each segment start. Missing bars are never
  fabricated.
- Prices compared on an integer tick grid (explicit tick_size + source); no
  floating epsilon.
- No look-ahead: a pivot/pool is usable only after its right-side confirmation
  bar has closed.
- Stable event order: (bar_start_ts, event_priority, level_price_ticks, level_id).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from gate0.canonical_bars import Bar, validate_series

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
    pivot_time: datetime        # bar_start of the pivot bar
    confirmation_time: datetime  # bar_end of the 2nd right-side bar
    pivot_id: str


@dataclass(frozen=True)
class Pool:
    kind: str  # "high" | "low"
    reference_price: float
    member_ids: tuple[str, ...]
    confirmation_time: datetime  # available only after the last member confirms
    tick_size: float
    tick_size_source: str


@dataclass(frozen=True)
class StructureEvent:
    type: str
    bar_start_ts: datetime
    direction: str  # "up" | "down" | "none"
    level_price: float | None
    level_id: str | None


@dataclass(frozen=True)
class StructureResult:
    events: list[StructureEvent] = field(default_factory=list)
    pivots: list[Pivot] = field(default_factory=list)
    pools: list[Pool] = field(default_factory=list)


def _ticks(price: float, tick: float) -> int:
    return round(price / tick)


def _segment(bars: list[Bar]) -> list[list[Bar]]:
    """Split into contiguous runs (next.start == prev.end). Gaps/overnight break."""
    segments: list[list[Bar]] = []
    cur: list[Bar] = []
    for b in bars:
        if cur and b.bar_start_ts != cur[-1].bar_end_ts:
            segments.append(cur)
            cur = []
        cur.append(b)
    if cur:
        segments.append(cur)
    return segments


def _swings(seg: list[Bar], instrument: str) -> list[Pivot]:
    """Strict 2-left/2-right swing pivots; confirmed after the 2nd right bar."""
    out: list[Pivot] = []
    for i in range(2, len(seg) - 2):
        hi = seg[i].high
        lo = seg[i].low
        others = (seg[i - 2], seg[i - 1], seg[i + 1], seg[i + 2])
        if all(hi > o.high for o in others):
            out.append(Pivot("high", hi, seg[i].bar_start_ts, seg[i + 2].bar_end_ts,
                             f"{instrument}:{seg[i].bar_start_ts.isoformat()}:H"))
        if all(lo < o.low for o in others):
            out.append(Pivot("low", lo, seg[i].bar_start_ts, seg[i + 2].bar_end_ts,
                             f"{instrument}:{seg[i].bar_start_ts.isoformat()}:L"))
    return out


def _confirmed_before(pivots: list[Pivot], kind: str, before_ts: datetime) -> Pivot | None:
    """Latest pivot of `kind` whose confirmation_time is strictly before `before_ts`."""
    best: Pivot | None = None
    for p in pivots:
        if p.kind == kind and p.confirmation_time < before_ts:
            if best is None or p.pivot_time > best.pivot_time:
                best = p
    return best


def _pools(seg: list[Bar], instrument: str, tick: float, source: str) -> list[Pool]:
    """Equal-extreme liquidity pools (>= with >=1 strict inequality; tick grouping)."""
    pools: list[Pool] = []
    for kind, pick in (("high", lambda b: b.high), ("low", lambda b: b.low)):
        candidates: list[tuple[float, datetime, str]] = []
        for i in range(2, len(seg) - 2):
            v = pick(seg[i])
            neigh = (seg[i - 2], seg[i - 1], seg[i + 1], seg[i + 2])
            vals = [pick(n) for n in neigh]
            if kind == "high":
                ok = all(v >= x for x in vals) and any(v > x for x in vals)
            else:
                ok = all(v <= x for x in vals) and any(v < x for x in vals)
            if ok:
                cid = f"{instrument}:{seg[i].bar_start_ts.isoformat()}:{'EH' if kind == 'high' else 'EL'}"
                candidates.append((v, seg[i + 2].bar_end_ts, cid))
        # Deterministic clustering by price on the tick grid: sort, group where
        # consecutive prices are within one tick.
        candidates.sort(key=lambda c: (_ticks(c[0], tick), c[1], c[2]))
        cluster: list[tuple[float, datetime, str]] = []
        for cand in candidates:
            if cluster and abs(_ticks(cand[0], tick) - _ticks(cluster[-1][0], tick)) > 1:
                pools.extend(_make_pool(kind, cluster, tick, source))
                cluster = []
            cluster.append(cand)
        pools.extend(_make_pool(kind, cluster, tick, source))
    return pools


def _make_pool(kind, cluster, tick, source) -> list[Pool]:
    if len(cluster) < 2:  # a pool needs >= 2 equal extremes
        return []
    prices = sorted(c[0] for c in cluster)
    n = len(prices)
    med = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    med = round(med / tick) * tick
    member_ids = tuple(sorted(c[2] for c in cluster))
    confirmation_time = max(c[1] for c in cluster)
    return [Pool(kind, med, member_ids, confirmation_time, tick, source)]


def _run_state_machine(seg: list[Bar], pivots: list[Pivot], tick: float, buffer_ticks: int) -> list[StructureEvent]:
    buffer = buffer_ticks * tick
    state = "NEUTRAL"
    protected_low: Pivot | None = None
    protected_high: Pivot | None = None
    protection_pending = False
    events: list[StructureEvent] = []

    for b in seg:
        ts = b.bar_start_ts
        close = b.close
        sh = _confirmed_before(pivots, "high", ts)
        sl = _confirmed_before(pivots, "low", ts)
        broke_high = sh is not None and close > sh.price + buffer
        broke_low = sl is not None and close < sl.price - buffer

        if state == "NEUTRAL":
            if broke_high and broke_low:
                events.append(StructureEvent(AMBIGUOUS_DOUBLE_BREAK, ts, "none", None, None))
            elif broke_high and sl is not None:
                events.append(StructureEvent(BOS_UP, ts, "up", sh.price, sh.pivot_id))
                state, protected_low, protection_pending = "BULL", sl, False
            elif broke_low and sh is not None:
                events.append(StructureEvent(BOS_DOWN, ts, "down", sl.price, sl.pivot_id))
                state, protected_high, protection_pending = "BEAR", sh, False

        elif state == "BULL":
            if (not protection_pending) and protected_low is not None and close < protected_low.price - buffer:
                events.append(StructureEvent(CHOCH_DOWN, ts, "down", protected_low.price, protected_low.pivot_id))
                state = "BEAR"
                newsh = _confirmed_before(pivots, "high", ts)
                if newsh is None:
                    protected_high, protection_pending = None, True
                    events.append(StructureEvent(PROTECTION_PENDING, ts, "down", None, None))
                else:
                    protected_high, protection_pending = newsh, False
            elif broke_high:
                events.append(StructureEvent(BOS_UP, ts, "up", sh.price, sh.pivot_id))
                newsl = _confirmed_before(pivots, "low", ts)
                protected_low = newsl
                protection_pending = newsl is None

        elif state == "BEAR":
            if (not protection_pending) and protected_high is not None and close > protected_high.price + buffer:
                events.append(StructureEvent(CHOCH_UP, ts, "up", protected_high.price, protected_high.pivot_id))
                state = "BULL"
                newsl = _confirmed_before(pivots, "low", ts)
                if newsl is None:
                    protected_low, protection_pending = None, True
                    events.append(StructureEvent(PROTECTION_PENDING, ts, "up", None, None))
                else:
                    protected_low, protection_pending = newsl, False
            elif broke_low:
                events.append(StructureEvent(BOS_DOWN, ts, "down", sl.price, sl.pivot_id))
                newsh = _confirmed_before(pivots, "high", ts)
                protected_high = newsh
                protection_pending = newsh is None

    return events


def detect_structure(
    bars: list[Bar],
    *,
    tick_size: float,
    tick_size_source: str,
    buffer_ticks: int = 0,
) -> StructureResult:
    """Detect §7.1-7.3 structure on a validated completed-5m series (one instrument).

    Fail-closed: raises ValueError on empty input, invalid series, mixed
    instrument/timeframe, or non-5m bars.
    """
    if not bars:
        raise ValueError("empty input: structure detection requires >= 1 completed 5m bar")
    if tick_size <= 0:
        raise ValueError("tick_size must be positive")
    problems = validate_series(bars, require_complete=True)
    if problems:
        raise ValueError(f"invalid bar series (fail-closed): {problems[:5]}")
    if any(b.timeframe != "5m" for b in bars):
        raise ValueError("structure operates on 5m bars only")
    instrument = bars[0].instrument_id

    all_events: list[StructureEvent] = []
    all_pivots: list[Pivot] = []
    all_pools: list[Pool] = []
    for seg in _segment(bars):
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
    return StructureResult(events=all_events, pivots=all_pivots, pools=all_pools)

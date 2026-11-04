"""Deterministic displacement detection (Gate 0 harness, Phase A) — spec v0.2 §7.4.

Pure, repository-only. No network/provider/credentials. Consumes validated
completed 5m `Bar`s plus an accepted `StructureResult` (BOS events + pivots) and
flags the single qualifying displacement sequence that confirms each BOS.

Implements ChatGPT scope agreement 029 (binding amendments 1-6):
- ATR(14): TR=max(h-l, |h-prev_close|, |l-prev_close|); first bar of a segment
  TR=h-l; Wilder seed = mean of first 14 TRs in the segment; then RMA
  ((prev*13)+tr)/14. The ATR used for a sequence starting at D1 is the value as
  of the bar immediately BEFORE D1 (prior completed bars only; no self-contribution).
  ATR resets at every session/gap boundary. No sequence is evaluable until 14
  prior TRs exist in the segment.
- Sequence: 1..sequence_max_len contiguous completed bars in one segment, each
  with a strictly positive body in the BOS direction (doji/opposite breaks it).
  Sequence net body = directional(first.open -> final.close), not summed bodies
  nor high-low range. The candidate must END on the BOS confirmation bar and its
  final close must be beyond that BOS's confirmed swing level. Among suffixes
  ending on the BOS bar, emit the SHORTEST qualifying one; at most one per BOS.
- Qualify iff net_body >= atr_mult * ATR_before_D1 (never substitute range).
- Volume modifier deferred: the optional field is always None here.
- Fail-closed validation; deterministic IDs and ordering.

Disposable audit tool; Python is not a production-stack decision (spec §14 open).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from gate0.canonical_bars import Bar, validate_series
from gate0.nse_calendar import TradingCalendar
from gate0.structure import (
    BOS_DOWN,
    BOS_UP,
    StructureResult,
    _on_grid,
    _segment,
)

SEQUENCE_MAX_LEN_CAP = 20  # documented upper bound on scanned sequence length
_ATR_PERIOD = 14


@dataclass(frozen=True)
class Displacement:
    displacement_id: str
    direction: str  # "up" | "down"
    bos_event_id: str
    bos_level_id: str
    bos_level_price: float
    bar_ids: tuple[str, ...]          # contributing bars, D1..E (bar_start isoformat)
    sequence_start_ts: datetime
    sequence_end_ts: datetime
    net_body: float
    atr_value: float
    atr_as_of_ts: datetime            # bar_end of the bar immediately before D1
    atr_mult: float
    threshold: float
    volume_flag: None = None          # deferred (amendment 5)


def _bar_id(b: Bar) -> str:
    return b.bar_start_ts.isoformat()


def _bos_event_id(instrument: str, ev) -> str:
    return f"{instrument}:{ev.bar_start_ts.isoformat()}:{ev.type}"


def _true_ranges(seg: list[Bar]) -> list[Decimal]:
    """True Range per bar, computed in Decimal from canonical bar values (D2).

    Precision policy: all TR/ATR arithmetic uses the Decimal default context
    (28 significant digits); no binary float is used until the public float
    output fields are constructed.
    """
    trs: list[Decimal] = []
    for i, b in enumerate(seg):
        h, l = Decimal(str(b.high)), Decimal(str(b.low))
        if i == 0:
            trs.append(h - l)
        else:
            pc = Decimal(str(seg[i - 1].close))
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return trs


def _atr_series(seg: list[Bar]) -> list[Decimal | None]:
    """Wilder ATR (Decimal) as-of each bar index; None before warm-up (index < 13)."""
    trs = _true_ranges(seg)
    atr: list[Decimal | None] = [None] * len(seg)
    period = Decimal(_ATR_PERIOD)
    if len(seg) >= _ATR_PERIOD:
        seed = sum(trs[:_ATR_PERIOD], Decimal(0)) / period
        atr[_ATR_PERIOD - 1] = seed
        prev = seed
        for i in range(_ATR_PERIOD, len(seg)):
            prev = ((prev * (period - 1)) + trs[i]) / period
            atr[i] = prev
    return atr


def _positive_body(b: Bar, direction: str) -> bool:
    return (b.close > b.open) if direction == "up" else (b.close < b.open)


def detect_displacement(
    bars: list[Bar],
    structure: StructureResult,
    *,
    calendar: TradingCalendar,
    tick_size: float,
    tick_size_source: str,
    displacement_atr_mult: float = 1.0,
    sequence_max_len: int = 10,
) -> list[Displacement]:
    # --- fail-closed validation (amendment 6) ---
    if not bars:
        raise ValueError("empty input")
    if not isinstance(calendar, TradingCalendar):
        raise ValueError("an explicit TradingCalendar is required")
    if not isinstance(structure, StructureResult):
        raise ValueError("a StructureResult is required")
    if not (isinstance(displacement_atr_mult, (int, float)) and math.isfinite(displacement_atr_mult)
            and displacement_atr_mult > 0):
        raise ValueError("displacement_atr_mult must be a finite positive number")
    if not (isinstance(tick_size, (int, float)) and math.isfinite(tick_size) and tick_size > 0):
        raise ValueError("tick_size must be a finite positive number")
    if not (isinstance(tick_size_source, str) and tick_size_source.strip()):
        raise ValueError("tick_size_source must be a non-empty provenance string")
    if isinstance(sequence_max_len, bool) or not isinstance(sequence_max_len, int) \
            or not (1 <= sequence_max_len <= SEQUENCE_MAX_LEN_CAP):
        raise ValueError(f"sequence_max_len must be an int in 1..{SEQUENCE_MAX_LEN_CAP}")

    problems = validate_series(bars, require_complete=True)
    if problems:
        raise ValueError(f"invalid bar series (fail-closed): {problems[:5]}")
    if any(b.timeframe != "5m" for b in bars):
        raise ValueError("displacement operates on 5m bars only")
    for b in bars:
        if not all(_on_grid(v, tick_size) for v in (b.open, b.high, b.low, b.close)):
            raise ValueError(f"off-grid OHLC at {b.bar_start_ts.isoformat()}")

    instrument = bars[0].instrument_id
    pivot_by_id = {p.pivot_id: p for p in structure.pivots}

    # Locate each bar within its session segment (amendment 1/6: calendar segmentation).
    segments = _segment(bars, calendar, "5m")
    seg_of: dict[datetime, tuple[int, int]] = {}  # bar_start_ts -> (segment idx, index in segment)
    atr_by_seg: list[list[float | None]] = []
    for s_idx, seg in enumerate(segments):
        atr_by_seg.append(_atr_series(seg))
        for b_idx, b in enumerate(seg):
            seg_of[b.bar_start_ts] = (s_idx, b_idx)

    seen_bos: set[str] = set()
    out: list[Displacement] = []

    for ev in structure.events:
        if ev.type not in (BOS_UP, BOS_DOWN):
            continue
        direction = "up" if ev.type == BOS_UP else "down"
        bos_id = _bos_event_id(instrument, ev)
        if bos_id in seen_bos:
            raise ValueError(f"duplicate BOS event: {bos_id}")
        seen_bos.add(bos_id)
        # linkage validation (amendment 4 + D1 coherence)
        if ev.level_id is None or ev.level_id not in pivot_by_id:
            raise ValueError(f"BOS references an unresolved pivot: {ev.level_id}")
        if not ev.level_id.startswith(instrument + ":"):
            raise ValueError("BOS pivot belongs to a different instrument")
        if ev.bar_start_ts not in seg_of:
            raise ValueError("BOS confirmation bar not found in the supplied bar stream")

        piv = pivot_by_id[ev.level_id]
        # D1: event type <-> direction consistency
        if (ev.type == BOS_UP and ev.direction != "up") or (ev.type == BOS_DOWN and ev.direction != "down"):
            raise ValueError("BOS event type/direction mismatch")
        # D1: BOS_UP must reference a high pivot; BOS_DOWN a low pivot
        if piv.kind != ("high" if direction == "up" else "low"):
            raise ValueError("BOS direction does not match the referenced pivot kind")
        # D1: pivot must be confirmed strictly before the BOS confirmation bar
        if piv.confirmation_time >= ev.bar_start_ts:
            raise ValueError("referenced pivot was not confirmed before the BOS bar")
        # D1: finite, positive, on-tick event and pivot prices
        for pr in (ev.level_price, piv.price):
            if pr is None or not (isinstance(pr, (int, float)) and math.isfinite(pr)) or pr <= 0 \
                    or not _on_grid(pr, tick_size):
                raise ValueError("BOS/pivot price must be finite, positive and on-tick")
        # D1: event level price must match the referenced pivot price
        if Decimal(str(ev.level_price)) != Decimal(str(piv.price)):
            raise ValueError("BOS level price does not match the referenced pivot price")

        s_idx, e_idx = seg_of[ev.bar_start_ts]
        seg = segments[s_idx]
        atr = atr_by_seg[s_idx]
        end_bar = seg[e_idx]
        level = ev.level_price

        # final close must be beyond the BOS swing level in the BOS direction
        if direction == "up" and not (end_bar.close > level):
            continue
        if direction == "down" and not (end_bar.close < level):
            continue

        chosen: Displacement | None = None
        for L in range(1, sequence_max_len + 1):
            d1 = e_idx - L + 1
            if d1 < 0:
                break  # cannot grow longer within the segment
            if d1 - 1 < _ATR_PERIOD - 1 or atr[d1 - 1] is None:
                continue  # not enough prior warm-up for this (or any longer) start
            seq = seg[d1:e_idx + 1]
            if not all(_positive_body(b, direction) for b in seq):
                continue
            first, final = seq[0], seq[-1]
            # D2: deterministic decimal comparison (no binary FP, no epsilon).
            net_body_dec = (Decimal(str(final.close)) - Decimal(str(first.open))) if direction == "up" \
                else (Decimal(str(first.open)) - Decimal(str(final.close)))
            if net_body_dec <= 0:
                continue
            atr_before = atr[d1 - 1]  # Decimal
            threshold_dec = Decimal(str(displacement_atr_mult)) * atr_before
            net_body = float(net_body_dec)
            threshold = float(threshold_dec)
            if net_body_dec >= threshold_dec:
                chosen = Displacement(
                    displacement_id=f"{bos_id}:DISP",
                    direction=direction,
                    bos_event_id=bos_id,
                    bos_level_id=ev.level_id,
                    bos_level_price=level,
                    bar_ids=tuple(_bar_id(b) for b in seq),
                    sequence_start_ts=first.bar_start_ts,
                    sequence_end_ts=final.bar_start_ts,
                    net_body=net_body,
                    atr_value=float(atr_before),
                    atr_as_of_ts=seg[d1 - 1].bar_end_ts,
                    atr_mult=displacement_atr_mult,
                    threshold=threshold,
                )
                break  # shortest qualifying wins (amendment 2)
        if chosen is not None:
            out.append(chosen)

    out.sort(key=lambda d: (d.sequence_end_ts, d.bos_event_id))
    return out

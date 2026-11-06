"""Universe-scan orchestration (Gate 0 harness, Phase A) — spec v0.3 §4-§6.

Pure, repository-only. No network/provider/credentials. Wires the already-
accepted/implemented pieces together into the one pipeline the spec
describes end to end (§6): **50-stock cash-equity scan -> 15m ranking ->
up to 5 bullish + 5 bearish Stage 1 shortlist -> 5m setup validation ->
up to 2 bullish + 2 bearish final candidates, selected independently per
direction, or NO TRADE per direction.**

This module does not fetch, validate against a live account, or compute
anything a provider-facing module does not already compute — it only
sequences `structure.py`, `displacement.py`, `ranking.py`, `zones.py` and
`setup.py` over a caller-supplied batch of per-symbol bars, exactly the
same whether that batch came from a historical pull (backtest) or a live
snapshot (per §7.1's "only the data adapter differs" principle).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from gate0.canonical_bars import Bar, validate_series
from gate0.displacement import Displacement, detect_displacement
from gate0.nse_calendar import TradingCalendar
from gate0.ranking import (
    NEUTRAL_BAND_DEFAULT,
    QUALIFYING_FLOOR_DEFAULT,
    RS_DEFAULT_THRESHOLD_PCT,
    Shortlist,
    SymbolScore,
    build_shortlist,
    current_structure_state,
    resolve_neutral_band,
    score_symbol,
)
from gate0.setup import SetupEvaluation, evaluate_setup, select_final_candidates
from gate0.structure import StructureResult, detect_structure
from gate0.zones import Zone, advance_zone, build_zone

STATUS_UNIVERSE_WIDE = "UNIVERSE_WIDE"
STATUS_PARTIAL = "PARTIAL"
STATUS_NO_TRADE = "NO_TRADE"

DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
STALE_LATEST_BAR = "STALE_LATEST_BAR"
MISALIGNED_5M_DATA = "MISALIGNED_5M_DATA"
INSTRUMENT_ID_MISMATCH = "INSTRUMENT_ID_MISMATCH"
COVERAGE_BELOW_THRESHOLD = "COVERAGE_BELOW_THRESHOLD"
NO_DIRECTIONAL_EDGE = "NO_DIRECTIONAL_EDGE"

DEFAULT_COVERAGE_THRESHOLD = 35  # provisional default noted in §6 -- NOT locked; configurable


class ScanInputError(ValueError):
    """Fail-closed: malformed input to the universe scan."""


@dataclass(frozen=True)
class SymbolBars:
    symbol: str
    bars_15m: list[Bar]
    bars_5m: list[Bar]
    volume_baseline: float | None = None
    tick_size: float = 0.05
    tick_size_source: str = "nse-default-tick"


@dataclass(frozen=True)
class ScanConfig:
    coverage_threshold: int = DEFAULT_COVERAGE_THRESHOLD  # out of len(symbols); provisional (§6)
    approach: str = "B"  # §5.4's recommended v1 default
    boundary_type: str = "full_range"
    qualifying_floor: int = QUALIFYING_FLOOR_DEFAULT
    neutral_band: int = NEUTRAL_BAND_DEFAULT
    rs_threshold_pct: Decimal = RS_DEFAULT_THRESHOLD_PCT
    displacement_atr_mult: float = 1.0
    max_stage1_shortlist: int = 5
    max_final_candidates: int = 2


@dataclass(frozen=True)
class SymbolHealth:
    symbol: str
    healthy: bool
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DirectionResult:
    direction: str  # "up" | "down"
    status: str  # UNIVERSE_WIDE | PARTIAL | NO_TRADE
    candidates: tuple[SetupEvaluation, ...]
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScannerRow:
    """§10 "Scanner: all 50 rows" -- one row per supplied symbol, healthy or
    not. `ltp` is the latest close at the scan's as-of time (None for an
    unhealthy symbol, since there is no trustworthy as-of price to show)."""
    symbol: str
    healthy: bool
    reason_codes: tuple[str, ...]
    ltp: float | None
    bull_total: int | None
    bear_total: int | None
    bull_eligible: bool | None
    bear_eligible: bool | None


@dataclass(frozen=True)
class ScanResult:
    healthy_count: int
    total: int
    health: tuple[SymbolHealth, ...]
    rows: tuple[ScannerRow, ...]
    stage1_shortlist: Shortlist
    bullish: DirectionResult
    bearish: DirectionResult


def _is_healthy(sb: SymbolBars) -> bool:
    if not sb.bars_15m or not sb.bars_5m:
        return False
    if validate_series(sb.bars_15m, require_complete=True):
        return False
    if validate_series(sb.bars_5m, require_complete=True):
        return False
    # Review 052: both series are individually validated above, but nothing
    # compared their instrument identities -- a mismatched pair (e.g. a
    # provider-side mix-up handing one symbol's 15m bars alongside another
    # symbol's 5m bars) would otherwise let Stage 1 rank one stock while
    # Stage 2 silently validates a different one. Checked here (not just
    # inside run_universe_scan's own health gate) so any other caller of
    # `_is_healthy` gets the same protection; `run_universe_scan` still
    # reports the specific `INSTRUMENT_ID_MISMATCH` reason code separately.
    if sb.bars_15m[0].instrument_id != sb.bars_5m[0].instrument_id:
        return False
    return True


def _instrument_ids_match(sb: SymbolBars) -> bool:
    return sb.bars_15m[0].instrument_id == sb.bars_5m[0].instrument_id


def _unhealthy_row(h: SymbolHealth) -> ScannerRow:
    return ScannerRow(symbol=h.symbol, healthy=False, reason_codes=h.reason_codes,
                      ltp=None, bull_total=None, bear_total=None, bull_eligible=None, bear_eligible=None)


def resolve_target_price(structure: StructureResult, direction: str, current_price: float) -> float | None:
    """§5.5: "the next opposing confirmed swing/liquidity level from
    `structure`. If none is objectively identified, mark the setup
    ineligible." An "up" trade's target is the nearest confirmed swing
    HIGH strictly above the current price; a "down" trade's target is the
    nearest confirmed swing LOW strictly below it. Returns None (never
    invents a target) if no such confirmed pivot exists."""
    if direction not in ("up", "down"):
        raise ScanInputError(f"invalid direction: {direction}")
    kind = "high" if direction == "up" else "low"
    candidates = [p.price for p in structure.pivots if p.kind == kind]
    if direction == "up":
        above = [p for p in candidates if p > current_price]
        return min(above) if above else None
    below = [p for p in candidates if p < current_price]
    return max(below) if below else None


def _latest_matching_displacement(displacements: list[Displacement], direction: str) -> Displacement | None:
    matching = [d for d in displacements if d.direction == direction]
    if not matching:
        return None
    return max(matching, key=lambda d: d.sequence_end_ts)


def _evaluate_candidate(
    sb: SymbolBars, direction: str, stage1_score: SymbolScore, *, calendar: TradingCalendar, config: ScanConfig,
) -> SetupEvaluation | None:
    structure = detect_structure(sb.bars_5m, calendar=calendar, tick_size=sb.tick_size,
                                 tick_size_source=sb.tick_size_source)
    displacements = detect_displacement(sb.bars_5m, structure, calendar=calendar, tick_size=sb.tick_size,
                                        tick_size_source=sb.tick_size_source,
                                        displacement_atr_mult=config.displacement_atr_mult)
    disp = _latest_matching_displacement(displacements, direction)
    if disp is None:
        return None  # no qualifying displacement in this direction -> no Stage 2 candidate at all

    zone = build_zone(disp, sb.bars_5m, calendar=calendar, approach=config.approach,
                      boundary_type=config.boundary_type)
    if zone is None:
        return None  # Approach A NO_ANCHOR_CANDLE -- no zone to evaluate
    zone = advance_zone(zone, sb.bars_5m, calendar=calendar)

    structure_state = current_structure_state(structure, sb.bars_15m, index=len(sb.bars_15m) - 1, calendar=calendar)
    current_price = sb.bars_5m[-1].close
    target_price = resolve_target_price(structure, direction, current_price)

    return evaluate_setup(
        sb.symbol, direction, structure_state=structure_state, zone=zone,
        stage1_score=stage1_score.detail.total, target_price=target_price,
    )


def run_universe_scan(
    symbols: list[SymbolBars],
    nifty_bars_15m: list[Bar],
    *,
    calendar: TradingCalendar,
    config: ScanConfig = ScanConfig(),
) -> ScanResult:
    """§4-§6 end to end, for one as-of point -- the universe's shared clock,
    the latest supplied Nifty 15m bar. Each symbol is scored independently;
    a symbol's own data problem never blocks any other symbol (§3.2's
    per-symbol `DATA_UNAVAILABLE`, never a global failure).

    **Review 050 fix:** every symbol used to be ranked "as of" its OWN
    latest supplied 15m bar (`len(sb.bars_15m) - 1`), with no check that
    this was actually the same wall-clock bar as Nifty's latest. A symbol
    missing only its single most-recent candle would silently be ranked one
    bar stale relative to the rest of the universe -- `validate_series`
    does not check expected-slot coverage, and `rs_score`'s own timestamp
    check only compares the two arrays AT THE SAME INDEX, which stays
    internally consistent even when that shared index is each symbol's own
    stale "latest," not the universe's actual latest. Fixed: every symbol's
    latest 15m bar must equal Nifty's latest 15m bar's timestamp, checked
    BEFORE scoring; otherwise the symbol is `DATA_UNAVAILABLE`
    (`STALE_LATEST_BAR`), never silently ranked at an older point in time.

    **Review 051 fix:** fixing the 15m/Nifty alignment above was not
    sufficient -- `_evaluate_candidate` separately consumes the symbol's
    *entire* 5m series (for `detect_structure`/`detect_displacement`, the
    zone lifecycle, and `current_price = bars_5m[-1].close`) with no check
    against the 15m as-of time at all. Stage 2 (5m) must validate the SAME
    market moment Stage 1 (15m) selected, per §4.8 -- not an older moment
    (stale 5m data behind the reference time) and not a newer one (5m bars
    extending past it, which would let future price action leak into the
    decision as look-ahead). Fixed with the simplest precondition for this
    single-as-of-point design: a symbol's latest completed 5m bar must end
    at exactly the same timestamp as its latest 15m bar; otherwise
    `DATA_UNAVAILABLE` (`MISALIGNED_5M_DATA`).
    """
    if not nifty_bars_15m:
        raise ScanInputError("nifty_bars_15m must not be empty")
    universe_latest_ts = nifty_bars_15m[-1].bar_start_ts

    total = len(symbols)
    health: list[SymbolHealth] = []
    rows: list[ScannerRow] = []
    scores: list[tuple[SymbolScore | None, SymbolScore | None]] = []
    score_by_symbol: dict[str, tuple[SymbolScore | None, SymbolScore | None]] = {}
    healthy_symbols: list[SymbolBars] = []

    for sb in symbols:
        if sb.bars_15m and sb.bars_5m and not _instrument_ids_match(sb):
            h = SymbolHealth(sb.symbol, healthy=False, reason_codes=(INSTRUMENT_ID_MISMATCH,))
            health.append(h); rows.append(_unhealthy_row(h))
            continue
        if not _is_healthy(sb):
            h = SymbolHealth(sb.symbol, healthy=False, reason_codes=(DATA_UNAVAILABLE,))
            health.append(h); rows.append(_unhealthy_row(h))
            continue
        if sb.bars_15m[-1].bar_start_ts != universe_latest_ts:
            h = SymbolHealth(sb.symbol, healthy=False, reason_codes=(STALE_LATEST_BAR,))
            health.append(h); rows.append(_unhealthy_row(h))
            continue
        if sb.bars_5m[-1].bar_end_ts != sb.bars_15m[-1].bar_end_ts:
            # Review 051: Stage 2 (5m) must validate the SAME as-of market
            # moment Stage 1 (15m) selected -- not an older one (stale 5m
            # data behind the scan's reference time) and not a newer one
            # (5m bars extending past it, which would let future price
            # action leak into the decision as look-ahead). The simplest
            # precondition for this single-as-of-point design: the latest
            # completed 5m bar must end exactly when the latest 15m bar
            # ends. No new subsystem -- this is the same per-symbol health
            # check the staleness fix above already uses.
            h = SymbolHealth(sb.symbol, healthy=False, reason_codes=(MISALIGNED_5M_DATA,))
            health.append(h); rows.append(_unhealthy_row(h))
            continue
        healthy_symbols.append(sb)
        index = len(sb.bars_15m) - 1
        structure_for_ranking = detect_structure(sb.bars_5m, calendar=calendar, tick_size=sb.tick_size,
                                                 tick_size_source=sb.tick_size_source)
        bull = score_symbol(sb.symbol, "up", stock_bars_15m=sb.bars_15m, nifty_bars_15m=nifty_bars_15m,
                            structure=structure_for_ranking, index=index, calendar=calendar,
                            volume_baseline=sb.volume_baseline, rs_threshold_pct=config.rs_threshold_pct,
                            qualifying_floor=config.qualifying_floor)
        bear = score_symbol(sb.symbol, "down", stock_bars_15m=sb.bars_15m, nifty_bars_15m=nifty_bars_15m,
                            structure=structure_for_ranking, index=index, calendar=calendar,
                            volume_baseline=sb.volume_baseline, rs_threshold_pct=config.rs_threshold_pct,
                            qualifying_floor=config.qualifying_floor)
        if bull is None and bear is None:
            h = SymbolHealth(sb.symbol, healthy=False, reason_codes=(DATA_UNAVAILABLE,))
            health.append(h); rows.append(_unhealthy_row(h))
            continue
        health.append(SymbolHealth(sb.symbol, healthy=True))
        rows.append(ScannerRow(
            symbol=sb.symbol, healthy=True, reason_codes=(), ltp=sb.bars_15m[index].close,
            bull_total=bull.detail.total if bull is not None else None,
            bear_total=bear.detail.total if bear is not None else None,
            bull_eligible=bull.eligible if bull is not None else None,
            bear_eligible=bear.eligible if bear is not None else None,
        ))
        bull_in, bear_in = resolve_neutral_band(bull, bear, band=config.neutral_band)
        resolved = (bull if bull_in else None, bear if bear_in else None)
        scores.append(resolved)
        score_by_symbol[sb.symbol] = resolved

    healthy_count = sum(1 for h in health if h.healthy)
    stage1_shortlist = build_shortlist(scores, max_per_side=config.max_stage1_shortlist)
    bars_by_symbol = {sb.symbol: sb for sb in healthy_symbols}

    bullish_evals: list[SetupEvaluation] = []
    for s in stage1_shortlist.bullish:
        ev = _evaluate_candidate(bars_by_symbol[s.symbol], "up", s, calendar=calendar, config=config)
        if ev is not None:
            bullish_evals.append(ev)
    bearish_evals: list[SetupEvaluation] = []
    for s in stage1_shortlist.bearish:
        ev = _evaluate_candidate(bars_by_symbol[s.symbol], "down", s, calendar=calendar, config=config)
        if ev is not None:
            bearish_evals.append(ev)

    bullish_final = select_final_candidates(bullish_evals, direction="up", max_per_side=config.max_final_candidates)
    bearish_final = select_final_candidates(bearish_evals, direction="down", max_per_side=config.max_final_candidates)

    below_threshold = healthy_count < config.coverage_threshold
    bullish = _direction_result("up", bullish_final, below_threshold)
    bearish = _direction_result("down", bearish_final, below_threshold)

    return ScanResult(healthy_count=healthy_count, total=total, health=tuple(health), rows=tuple(rows),
                      stage1_shortlist=stage1_shortlist, bullish=bullish, bearish=bearish)


def _direction_result(direction: str, candidates: tuple[SetupEvaluation, ...], below_threshold: bool) -> DirectionResult:
    """§6: below the coverage threshold, a direction's result is labeled
    PARTIAL regardless of whether candidates were found among the available
    symbols -- distinct from NO_TRADE, which means full coverage was
    evaluated and genuinely none qualified. These two are never conflated."""
    if below_threshold:
        return DirectionResult(direction, STATUS_PARTIAL, candidates, (COVERAGE_BELOW_THRESHOLD,))
    if not candidates:
        return DirectionResult(direction, STATUS_NO_TRADE, candidates, (NO_DIRECTIONAL_EDGE,))
    return DirectionResult(direction, STATUS_UNIVERSE_WIDE, candidates, ())

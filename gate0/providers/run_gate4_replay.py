"""Gate 4 historical replay runner (Phase A, pure) — spec v0.3 §7.5-§7.7.

Pure, repository-only. No network/provider/credentials — unlike
`historical_audit.py`, this module reads only ALREADY-SAVED local CSVs
(written by `historical_audit.py --save-bars-dir`); it never calls
SmartAPI or touches the owner's account. Claude can run this module
directly, the same way it runs pytest, because nothing here is a live call.

**Why this exists:** prior runs of `historical_audit.py` only ever saved
`candle-coverage.csv` (counts, first/last timestamps) — never the actual
candles. §7.5/§7.7's comparison needs the real OHLCV series, which did not
exist on disk anywhere until `historical_audit.py` gained `--save-bars-dir`
(2026-11-06). This module is what consumes that output once it exists.

**Real NSE calendar required, not supplied here.** `structure.py`/
`zones.py`/`ranking.py` all require an explicit `TradingCalendar` built
from a real, versioned NSE holiday list for the replay window — this
module takes one as a parameter rather than inventing or guessing one;
`nse_calendar.py`'s own docstring is explicit that holiday data "must be
separately sourced and audited" and is not an authoritative source itself.

Two evidence-gathering modes, matching the two separate questions §7
asks (§7.7: the zone-model comparison does not by itself establish that
the full pipeline is useful — report both, never infer one from the other):

- `run_zone_comparison()`: §7.5's four-configuration comparison, pooled
  across every symbol supplied — each symbol's own displacements/bars feed
  all four configurations identically; only the zone-selection step varies.
- `run_walkforward()`: §7.7's full-pipeline validation — replays
  `scan.run_universe_scan()` chronologically across the supplied history
  at a configurable step, simulates every final candidate's outcome, and
  splits the result chronologically into a train and a holdout window
  (no tuning on the holdout, per §7.7's own instruction).

`generate_evidence_report()` renders both results, with their explicit
limitations, into the one report §7.5/§7.7 call for.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime

from gate0.backtest import (
    ZONE_CONFIGURATIONS,
    ConfigurationResult,
    TradeOutcome,
    summarize_outcomes,
    trade_outcomes_for_configuration,
)
from gate0.canonical_bars import Bar
from gate0.displacement import detect_displacement
from gate0.nse_calendar import TradingCalendar
from gate0.scan import ScanConfig, SymbolBars, run_universe_scan
from gate0.structure import detect_structure


class ReplayInputError(ValueError):
    """Fail-closed: malformed or missing input to the Gate 4 replay."""


def load_symbol_bars_csv(path: str, instrument_id: str, timeframe: str) -> list[Bar]:
    """Reads back one CSV written by `historical_audit.save_bars_csv()`."""
    bars: list[Bar] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            start = datetime.fromisoformat(row["bar_start_ts"])
            end = datetime.fromisoformat(row["bar_end_ts"])
            bars.append(Bar(
                instrument_id, timeframe, start, end,
                float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),
                float(row["volume"]),
            ))
    bars.sort(key=lambda b: b.bar_start_ts)
    return bars


def load_universe_from_dir(
    data_dir: str, symbols: list[str], index_symbol: str,
) -> tuple[dict[str, tuple[list[Bar], list[Bar]]], list[Bar]]:
    """Loads every symbol's (5m, 15m) bars plus the index's 15m bars from
    `data_dir`. A symbol whose CSVs are missing is skipped, not fabricated
    — §3.2's per-symbol DATA_UNAVAILABLE, never a global failure."""
    per_symbol: dict[str, tuple[list[Bar], list[Bar]]] = {}
    for sym in symbols:
        p5 = os.path.join(data_dir, f"{sym}_5m.csv")
        p15 = os.path.join(data_dir, f"{sym}_15m.csv")
        if not (os.path.exists(p5) and os.path.exists(p15)):
            continue
        per_symbol[sym] = (load_symbol_bars_csv(p5, sym, "5m"), load_symbol_bars_csv(p15, sym, "15m"))
    index_path = os.path.join(data_dir, f"{index_symbol}_15m.csv")
    if not os.path.exists(index_path):
        raise ReplayInputError(f"index 15m bars not found: {index_path}")
    nifty_15m = load_symbol_bars_csv(index_path, index_symbol, "15m")
    return per_symbol, nifty_15m


@dataclass(frozen=True)
class ZoneComparisonEvidence:
    configurations: dict[tuple[str, str], ConfigurationResult]
    overall_inconclusive: bool
    default_choice: tuple[str, str]
    symbols_included: int
    symbols_skipped_no_displacement: int


def run_zone_comparison(
    per_symbol: dict[str, tuple[list[Bar], list[Bar]]],
    *,
    calendar: TradingCalendar,
    target_resolver,
    config: ScanConfig = ScanConfig(),
) -> ZoneComparisonEvidence:
    """§7.5 pooled across every symbol in `per_symbol`. Each symbol's own
    displacements/bars feed all four configurations identically (the
    controlled-design requirement); outcomes are pooled across symbols
    before computing the evaluation measures, so the 100-qualified-setups
    bar is judged against the whole universe's evidence, not one symbol's.
    """
    pooled: dict[tuple[str, str], list[TradeOutcome]] = {cfg: [] for cfg in ZONE_CONFIGURATIONS}
    included = 0
    skipped = 0
    for symbol, (bars_5m, _bars_15m) in per_symbol.items():
        structure = detect_structure(bars_5m, calendar=calendar, tick_size=0.05, tick_size_source="gate4-replay")
        displacements = detect_displacement(bars_5m, structure, calendar=calendar, tick_size=0.05,
                                            tick_size_source="gate4-replay",
                                            displacement_atr_mult=config.displacement_atr_mult)
        if not displacements:
            skipped += 1
            continue
        included += 1
        for approach, boundary_type in ZONE_CONFIGURATIONS:
            outcomes = trade_outcomes_for_configuration(
                approach, boundary_type, displacements, bars_5m, calendar=calendar,
                target_resolver=target_resolver,
            )
            pooled[(approach, boundary_type)].extend(outcomes)

    results = {cfg: summarize_outcomes(cfg[0], cfg[1], outs) for cfg, outs in pooled.items()}
    return ZoneComparisonEvidence(
        configurations=results, overall_inconclusive=any(r.inconclusive for r in results.values()),
        default_choice=("B", "full_range"), symbols_included=included, symbols_skipped_no_displacement=skipped,
    )


@dataclass(frozen=True)
class WalkforwardWindowResult:
    window: str  # "train" | "holdout"
    as_of_points: int
    trades: tuple[TradeOutcome, ...]
    wins: int
    losses: int
    win_rate: float | None
    avg_net_rr: float | None


@dataclass(frozen=True)
class WalkforwardEvidence:
    train: WalkforwardWindowResult
    holdout: WalkforwardWindowResult
    split_ts: datetime


def _summarize_window(window: str, as_of_points: int, trades: list[TradeOutcome]) -> WalkforwardWindowResult:
    resolved = [t for t in trades if t.outcome in ("WIN", "LOSS")]
    wins = sum(1 for t in resolved if t.outcome == "WIN")
    losses = sum(1 for t in resolved if t.outcome == "LOSS")
    win_rate = (wins / len(resolved)) if resolved else None
    rr_values = [t.net_rr_after_costs for t in resolved if t.net_rr_after_costs is not None]
    avg_rr = (sum(rr_values) / len(rr_values)) if rr_values else None
    return WalkforwardWindowResult(window=window, as_of_points=as_of_points, trades=tuple(trades),
                                   wins=wins, losses=losses, win_rate=win_rate, avg_net_rr=avg_rr)


def run_walkforward(
    per_symbol: dict[str, tuple[list[Bar], list[Bar]]],
    nifty_15m: list[Bar],
    *,
    calendar: TradingCalendar,
    config: ScanConfig = ScanConfig(),
    step: int = 4,
    holdout_frac: float = 0.3,
) -> WalkforwardEvidence:
    """§7.7: replays `run_universe_scan` chronologically. At every `step`-th
    15m index of the Nifty series (the universe's shared clock), builds the
    as-of symbol bars by truncation (§7.1: only information available at
    each event time) and scans; each final candidate's zone is then
    simulated via `backtest.simulate_trade` against that symbol's FULL 5m
    series restricted to bars at/after the as-of point (still no
    look-ahead — the fill/outcome walk only consumes bars after the signal,
    which are legitimately "the future relative to the signal" within a
    historical replay, exactly as live trading would experience them).

    The chronological split (not random) means `train` is always the
    earlier `1 - holdout_frac` of as-of points and `holdout` the later
    `holdout_frac` — no tuning is performed on the holdout by this
    function or any caller is meant to perform afterward, per §7.7.
    """
    if not (0 < holdout_frac < 1):
        raise ReplayInputError("holdout_frac must be between 0 and 1")
    if step < 1:
        raise ReplayInputError("step must be >= 1")

    n = len(nifty_15m)
    indices = list(range(0, n, step))
    split_idx = int(len(indices) * (1 - holdout_frac))
    split_ts = nifty_15m[indices[split_idx]].bar_start_ts if split_idx < len(indices) else nifty_15m[-1].bar_start_ts

    from gate0.backtest import simulate_trade

    train_trades: list[TradeOutcome] = []
    holdout_trades: list[TradeOutcome] = []
    train_points = holdout_points = 0
    seen_zone_ids: set[str] = set()  # a confirmed zone is only simulated once, the first as-of point it appears

    for pos, i in enumerate(indices):
        as_of_ts = nifty_15m[i].bar_start_ts
        nifty_slice = nifty_15m[: i + 1]
        symbols_slice: list[SymbolBars] = []
        for symbol, (bars_5m, bars_15m) in per_symbol.items():
            b15 = [b for b in bars_15m if b.bar_start_ts <= as_of_ts]
            b5 = [b for b in bars_5m if b.bar_start_ts <= as_of_ts]
            if not b15 or not b5:
                continue
            symbols_slice.append(SymbolBars(symbol=symbol, bars_15m=b15, bars_5m=b5))
        if not symbols_slice:
            continue

        result = run_universe_scan(symbols_slice, nifty_slice, calendar=calendar, config=config)
        is_holdout = pos >= split_idx
        if is_holdout:
            holdout_points += 1
        else:
            train_points += 1

        for direction_result in (result.bullish, result.bearish):
            for candidate in direction_result.candidates:
                zone_id = candidate.zone.zone_id
                if zone_id in seen_zone_ids:
                    continue
                seen_zone_ids.add(zone_id)
                sb = next(sb for sb in symbols_slice if sb.symbol == candidate.symbol)
                full_bars_5m = per_symbol[candidate.symbol][0]
                outcome = simulate_trade(candidate.zone, full_bars_5m, target_price=candidate.target_price)
                (holdout_trades if is_holdout else train_trades).append(outcome)

    train = _summarize_window("train", train_points, train_trades)
    holdout = _summarize_window("holdout", holdout_points, holdout_trades)
    return WalkforwardEvidence(train=train, holdout=holdout, split_ts=split_ts)


def generate_evidence_report(
    zone_evidence: ZoneComparisonEvidence,
    walkforward_evidence: WalkforwardEvidence,
    *,
    window_description: str,
    known_limitations: list[str],
) -> str:
    """§7.5/§7.7: the one evidence report both results belong in — never
    inferring the full-pipeline answer from the zone comparison, or vice
    versa, per §7.7's own instruction."""
    lines = ["# Gate 4 historical replay — evidence report", "", f"**Window:** {window_description}", ""]

    lines += ["## §7.5 — Zone-model comparison (Approach A vs B, full-range vs body-only)", ""]
    lines += [f"Symbols with at least one qualifying displacement: {zone_evidence.symbols_included} "
             f"(skipped, no displacement: {zone_evidence.symbols_skipped_no_displacement})", ""]
    lines += ["| Configuration | Qualified | Wins | Losses | Open | Missed | Invalidated | Win rate | Avg net R:R | Inconclusive |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for (approach, boundary), r in zone_evidence.configurations.items():
        wr = f"{r.win_rate:.1%}" if r.win_rate is not None else "–"
        rr = f"{r.avg_realized_rr:.2f}" if r.avg_realized_rr is not None else "–"
        lines.append(f"| {approach}-{boundary} | {r.qualified_setups} | {r.wins} | {r.losses} | "
                     f"{r.open_trades} | {r.missed} | {r.invalidated} | {wr} | {rr} | {'YES' if r.inconclusive else 'no'} |")
    lines.append("")
    if zone_evidence.overall_inconclusive:
        lines.append(f"**Overall: INCONCLUSIVE** — at least one configuration is below the 100-qualified-setups "
                     f"evidence bar (§7.5). Retaining the v1 default per §5.4: "
                     f"**{zone_evidence.default_choice[0]}-{zone_evidence.default_choice[1]}**. "
                     "Not re-run on an enlarged sample merely to force a result.")
    else:
        lines.append("**Overall: evidence bar met for all four configurations** — see the table above for the "
                     "actual comparison; this report does not declare a winner on your behalf.")
    lines.append("")

    lines += ["## §7.7 — Full-pipeline validation (does Stage 1/Stage 2 add value?)", ""]
    for w in (walkforward_evidence.train, walkforward_evidence.holdout):
        wr = f"{w.win_rate:.1%}" if w.win_rate is not None else "–"
        rr = f"{w.avg_net_rr:.2f}" if w.avg_net_rr is not None else "–"
        lines.append(f"- **{w.window}**: {w.as_of_points} as-of scan points, {len(w.trades)} simulated trades "
                     f"({w.wins} wins / {w.losses} losses), win rate {wr}, avg net R:R {rr}")
    lines.append(f"- Chronological split at {walkforward_evidence.split_ts.isoformat()} — no tuning performed "
                 "on the holdout window by this report or its generation.")
    lines.append("")
    lines.append("No raw-RS-only or random-draw baseline is computed by this report — §7.7 asks for that "
                 "comparison explicitly; it is not yet implemented and is a known gap, not a silent omission.")
    lines.append("")

    lines += ["## Known limitations", ""]
    for item in known_limitations:
        lines.append(f"- {item}")
    lines.append("")
    lines += ["## What this report does NOT claim", "",
             "- No numeric pass/fail threshold is pre-approved for either section above (§7.7's own instruction).",
             "- This does not authorize Phase B live trading, order execution, or any change to the settled "
             "v0.3 scoring/zone-model decisions.",
             "- Win rate alone, in either section, is never sufficient to declare success."]
    return "\n".join(lines)

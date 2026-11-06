"""Chronological replay / backtest engine (Gate 0 harness, Phase A) —
spec v0.3 §7.1, §7.3, §7.5.

Pure, repository-only. No network/provider/credentials, no live data. This
is the **shared engine** (§7.1): it calls the same `structure`,
`displacement`, `zones` and `costs` code a live scan would use, over a
supplied historical bar series, using only information available at each
event's own time (no look-ahead). Only the data adapter (here: a plain
in-memory `Bar` list the caller supplies) and the execution simulator
(below) differ between live and backtest use.

Historical sourcing/depth (§7.2, §7.6) is explicitly out of scope here —
that is a Phase B, owner-run concern (SmartAPI batch pull). This module
only consumes whatever bars it is given; it never fetches, and a thin
synthetic series exercises it exactly like a real one would.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from gate0.canonical_bars import Bar
from gate0.costs import PLACEHOLDER_SCHEDULE, CostSchedule, round_trip_cost
from gate0.displacement import Displacement
from gate0.nse_calendar import TradingCalendar
from gate0.zones import STATE_INVALIDATED, STATE_TOUCHED, Zone, advance_zone, build_zone

OUTCOME_WIN = "WIN"
OUTCOME_LOSS = "LOSS"
OUTCOME_OPEN = "OPEN"  # neither stop nor target hit before the supplied data ran out
OUTCOME_MISSED = "MISSED"  # zone expired before confirmation -- no trade was ever taken
OUTCOME_INVALIDATED = "INVALIDATED"  # zone invalidated before confirmation -- no trade taken


class BacktestInputError(ValueError):
    """Fail-closed: malformed input to the replay engine."""


@dataclass(frozen=True)
class TradeOutcome:
    displacement_id: str
    approach: str  # "A" | "B"
    boundary_type: str
    direction: str
    outcome: str  # WIN | LOSS | OPEN | MISSED | INVALIDATED
    fill_ts: datetime | None
    fill_price: float | None
    exit_ts: datetime | None
    exit_price: float | None
    stop_price: float | None
    target_price: float | None
    mae: float | None  # maximum adverse excursion from fill_price, in price units (>= 0), None if never filled
    net_rr_after_costs: float | None  # None if never filled or outcome is OPEN


def _next_bar_after(bars: list[Bar], ts: datetime) -> Bar | None:
    """§7.3: the fill never happens on the signal bar's own close -- it is
    the next executable 5m bar strictly after `ts` (the confirmation bar's
    bar_start_ts)."""
    for b in bars:
        if b.bar_start_ts > ts:
            return b
    return None


def simulate_trade(
    zone: Zone,
    bars_5m: list[Bar],
    *,
    target_price: float | None,
    quantity: Decimal = Decimal(1),
    intraday: bool = True,
    cost_schedule: CostSchedule = PLACEHOLDER_SCHEDULE,
    spread_pct: Decimal = Decimal("0.0005"),
) -> TradeOutcome:
    """§7.3/§5.5: simulates one trade for an already-advanced `zone`.

    - `MISSED`/`INVALIDATED`: the zone never produced a confirmed entry (it
      expired or was invalidated first) -- no fill, no outcome price.
    - Otherwise: fill at the open of the next executable 5m bar strictly
      after the confirmation bar (never at the confirmation bar's own
      close), with a conservative spread applied against the trade
      direction. The trade is then walked forward bar-by-bar (stop checked
      before target each bar, the conservative order) until either the
      stop or `target_price` is touched, tracking MAE throughout. If the
      supplied data runs out first, the outcome is `OPEN` (unresolved, not
      a loss) and no cost/R:R is computed.
    """
    direction = zone.direction
    if direction not in ("up", "down"):
        raise BacktestInputError(f"invalid zone direction: {direction}")

    if zone.confirmed_ts is None or zone.state == STATE_INVALIDATED:
        outcome = OUTCOME_INVALIDATED if zone.state == STATE_INVALIDATED else OUTCOME_MISSED
        return TradeOutcome(
            displacement_id=zone.displacement_id, approach=zone.approach, boundary_type=zone.boundary_type,
            direction=direction, outcome=outcome, fill_ts=None, fill_price=None, exit_ts=None, exit_price=None,
            stop_price=zone.distal, target_price=target_price, mae=None, net_rr_after_costs=None,
        )

    fill_bar = _next_bar_after(bars_5m, zone.confirmed_ts)
    if fill_bar is None:
        return TradeOutcome(
            displacement_id=zone.displacement_id, approach=zone.approach, boundary_type=zone.boundary_type,
            direction=direction, outcome=OUTCOME_OPEN, fill_ts=None, fill_price=None, exit_ts=None, exit_price=None,
            stop_price=zone.distal, target_price=target_price, mae=None, net_rr_after_costs=None,
        )

    raw_fill = Decimal(str(fill_bar.open))
    fill_price_dec = raw_fill * (Decimal(1) + spread_pct) if direction == "up" else raw_fill * (Decimal(1) - spread_pct)
    fill_price = float(fill_price_dec)
    stop_price = zone.distal
    mae = Decimal(0)

    walk = [b for b in bars_5m if b.bar_start_ts >= fill_bar.bar_start_ts]
    for b in walk:
        adverse = (fill_price_dec - Decimal(str(b.low))) if direction == "up" else (Decimal(str(b.high)) - fill_price_dec)
        if adverse > mae:
            mae = adverse

        hit_stop = (b.low <= stop_price) if direction == "up" else (b.high >= stop_price)
        if hit_stop:
            exit_price = stop_price
            net_rr = _net_rr(fill_price_dec, Decimal(str(exit_price)), stop_price, target_price, direction,
                             quantity, intraday, cost_schedule)
            return TradeOutcome(
                displacement_id=zone.displacement_id, approach=zone.approach, boundary_type=zone.boundary_type,
                direction=direction, outcome=OUTCOME_LOSS, fill_ts=fill_bar.bar_start_ts, fill_price=fill_price,
                exit_ts=b.bar_start_ts, exit_price=exit_price, stop_price=stop_price, target_price=target_price,
                mae=float(mae), net_rr_after_costs=net_rr,
            )
        if target_price is not None:
            hit_target = (b.high >= target_price) if direction == "up" else (b.low <= target_price)
            if hit_target:
                net_rr = _net_rr(fill_price_dec, Decimal(str(target_price)), stop_price, target_price, direction,
                                 quantity, intraday, cost_schedule)
                return TradeOutcome(
                    displacement_id=zone.displacement_id, approach=zone.approach, boundary_type=zone.boundary_type,
                    direction=direction, outcome=OUTCOME_WIN, fill_ts=fill_bar.bar_start_ts, fill_price=fill_price,
                    exit_ts=b.bar_start_ts, exit_price=target_price, stop_price=stop_price, target_price=target_price,
                    mae=float(mae), net_rr_after_costs=net_rr,
                )

    return TradeOutcome(
        displacement_id=zone.displacement_id, approach=zone.approach, boundary_type=zone.boundary_type,
        direction=direction, outcome=OUTCOME_OPEN, fill_ts=fill_bar.bar_start_ts, fill_price=fill_price,
        exit_ts=None, exit_price=None, stop_price=stop_price, target_price=target_price,
        mae=float(mae), net_rr_after_costs=None,
    )


def _net_rr(
    fill_price: Decimal, exit_price: Decimal, stop_price: float, target_price: float | None,
    direction: str, quantity: Decimal, intraday: bool, cost_schedule: CostSchedule,
) -> float | None:
    risk = (fill_price - Decimal(str(stop_price))) if direction == "up" else (Decimal(str(stop_price)) - fill_price)
    if risk <= 0:
        return None
    gross_pnl = (exit_price - fill_price) * quantity if direction == "up" else (fill_price - exit_price) * quantity
    entry_for_cost, exit_for_cost = (fill_price, exit_price) if direction == "up" else (exit_price, fill_price)
    cost = round_trip_cost(entry_for_cost, exit_for_cost, quantity, intraday=intraday, schedule=cost_schedule)
    net_pnl = gross_pnl - cost
    return float(net_pnl / (risk * quantity))


ZONE_CONFIGURATIONS = (("A", "full_range"), ("A", "body_only"), ("B", "full_range"), ("B", "body_only"))
MIN_QUALIFIED_SETUPS = 100  # §7.5 minimum-evidence bar, per configuration


@dataclass(frozen=True)
class ConfigurationResult:
    approach: str
    boundary_type: str
    qualified_setups: int
    wins: int
    losses: int
    open_trades: int
    missed: int
    invalidated: int
    win_rate: float | None  # among resolved (WIN/LOSS) trades; None if none resolved
    avg_realized_rr: float | None  # among resolved trades with a computed net R:R
    expectancy_after_costs: float | None  # avg net R:R across ALL qualified setups (OPEN excluded)
    inconclusive: bool  # True if qualified_setups < MIN_QUALIFIED_SETUPS (§7.5)


@dataclass(frozen=True)
class ComparisonResult:
    configurations: dict[tuple[str, str], ConfigurationResult]
    overall_inconclusive: bool
    default_choice: tuple[str, str]  # retained default when inconclusive: ("B", "full_range")


def trade_outcomes_for_configuration(
    approach: str, boundary_type: str, displacements: list[Displacement], bars_5m: list[Bar],
    *, calendar: TradingCalendar, target_resolver, quantity: Decimal = Decimal(1),
    intraday: bool = True, cost_schedule: CostSchedule = PLACEHOLDER_SCHEDULE,
) -> list[TradeOutcome]:
    """The raw per-displacement outcomes for one (approach, boundary_type)
    configuration, for ONE instrument's own displacements/bars. Exposed
    publicly (not just via `compare_zone_configurations`) so a caller
    running many instruments (e.g. a full-universe Gate 4 replay) can pool
    outcomes across instruments before summarizing -- `summarize_outcomes`
    does that summarizing step, shared by both call paths.
    """
    outcomes: list[TradeOutcome] = []
    for disp in displacements:
        zone = build_zone(disp, bars_5m, calendar=calendar, approach=approach, boundary_type=boundary_type)
        if zone is None:
            continue  # Approach A NO_ANCHOR_CANDLE -- no zone, not counted as a qualified setup either way
        zone = advance_zone(zone, bars_5m, calendar=calendar)
        target_price = target_resolver(disp)
        outcome = simulate_trade(zone, bars_5m, target_price=target_price, quantity=quantity,
                                 intraday=intraday, cost_schedule=cost_schedule)
        outcomes.append(outcome)
    return outcomes


def summarize_outcomes(approach: str, boundary_type: str, outcomes: list[TradeOutcome]) -> ConfigurationResult:
    """§7.5's evaluation measures computed from an already-gathered list of
    `TradeOutcome` (one instrument's own, or many instruments pooled)."""
    qualified = [o for o in outcomes if o.outcome in (OUTCOME_WIN, OUTCOME_LOSS, OUTCOME_OPEN)]
    wins = sum(1 for o in outcomes if o.outcome == OUTCOME_WIN)
    losses = sum(1 for o in outcomes if o.outcome == OUTCOME_LOSS)
    opens = sum(1 for o in outcomes if o.outcome == OUTCOME_OPEN)
    missed = sum(1 for o in outcomes if o.outcome == OUTCOME_MISSED)
    invalidated = sum(1 for o in outcomes if o.outcome == OUTCOME_INVALIDATED)

    resolved = [o for o in outcomes if o.outcome in (OUTCOME_WIN, OUTCOME_LOSS)]
    win_rate = (wins / len(resolved)) if resolved else None
    rr_values = [o.net_rr_after_costs for o in resolved if o.net_rr_after_costs is not None]
    avg_rr = (sum(rr_values) / len(rr_values)) if rr_values else None
    expectancy_values = [o.net_rr_after_costs for o in qualified if o.net_rr_after_costs is not None]
    expectancy = (sum(expectancy_values) / len(expectancy_values)) if expectancy_values else None

    return ConfigurationResult(
        approach=approach, boundary_type=boundary_type, qualified_setups=len(qualified),
        wins=wins, losses=losses, open_trades=opens, missed=missed, invalidated=invalidated,
        win_rate=win_rate, avg_realized_rr=avg_rr, expectancy_after_costs=expectancy,
        inconclusive=len(qualified) < MIN_QUALIFIED_SETUPS,
    )


def compare_zone_configurations(
    displacements: list[Displacement],
    bars_5m: list[Bar],
    *,
    calendar: TradingCalendar,
    target_resolver,
    quantity: Decimal = Decimal(1),
    intraday: bool = True,
    cost_schedule: CostSchedule = PLACEHOLDER_SCHEDULE,
) -> ComparisonResult:
    """§7.5: runs all four configurations (A-full, A-body, B-full, B-body)
    over the SAME displacements/bars/calendar -- the only thing that varies
    is the zone-selection step, exactly as the controlled-design protocol
    requires. `target_resolver(displacement) -> float | None` supplies
    §5.5's "next opposing confirmed swing/liquidity level"; this module does
    not derive it itself (that is the caller's `structure.py` lookup).

    Per §7.5: any configuration with fewer than `MIN_QUALIFIED_SETUPS`
    qualified setups is `inconclusive=True` and must be reported as such,
    never used to declare a winner. If the overall comparison is
    inconclusive, `default_choice` names the retained v1 default
    (`("B", "full_range")`, per §5.4's recommendation) rather than
    forcing a declared winner from insufficient evidence.
    """
    results: dict[tuple[str, str], ConfigurationResult] = {}
    for approach, boundary_type in ZONE_CONFIGURATIONS:
        outcomes = trade_outcomes_for_configuration(
            approach, boundary_type, displacements, bars_5m, calendar=calendar,
            target_resolver=target_resolver, quantity=quantity, intraday=intraday, cost_schedule=cost_schedule,
        )
        results[(approach, boundary_type)] = summarize_outcomes(approach, boundary_type, outcomes)
    overall_inconclusive = any(r.inconclusive for r in results.values())
    return ComparisonResult(configurations=results, overall_inconclusive=overall_inconclusive,
                            default_choice=("B", "full_range"))

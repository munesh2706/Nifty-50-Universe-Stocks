"""Stage 2 (5m) setup validation — spec v0.3 §4.8, §5.5, §5.7.

Pure, repository-only. No network/provider/credentials. Applies the three
locked qualitative Stage 2 selection questions (§4.8) on top of the
already-built `Zone` (zones.py, §5.3/§5.4) for each Stage 1 candidate,
computes net reward:risk directly on the cash-equity price (§5.5 — there is
no premium/Greeks/futures-basis model), and selects up to two eligible
survivors per direction (§4.8), never pooled across directions (§4.9/A-10).

§4.8's three questions, as implemented here:

1. **Directional confirmation** — the symbol's `structure.py` state (as of
   the 15m ranking grid, already computed by `ranking.structure_score`'s
   caller) and the zone's own direction must both agree with the candidate's
   claimed direction.
2. **Reachable entry** — the zone must have actually produced a confirmed
   entry-trigger bar (`zone.confirmed_ts`, §5.3 rule 6) and must not be
   `INVALIDATED`. A zone that merely touched but never confirmed, or that
   `EXPIRED` first, has no reachable entry.
3. **Defensible stop and target** — an objectively identified target
   (§5.5: "the next opposing confirmed swing/liquidity level from
   `structure`... If none is objectively identified, mark the setup
   ineligible") and a net R:R at/above the provisional research threshold.

A candidate failing any of the three is ineligible regardless of its Stage 1
score (§4.8). The R:R numeric floor is a provisional research hypothesis,
not a proven production value (§5.5) — explicitly configurable, not hard-
coded as a locked constant.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from gate0.zones import STATE_INVALIDATED, Zone

NET_RR_PROVISIONAL_THRESHOLD = Decimal("1.5")  # research hypothesis (§5.5) -- not locked

# §5.7 reason codes relevant to Stage 2 (per-candidate)
NO_DIRECTIONAL_EDGE = "NO_DIRECTIONAL_EDGE"
NO_FRESH_SETUP = "NO_FRESH_SETUP"
ZONE_INVALIDATED = "ZONE_INVALIDATED"
ENTRY_TOO_EXTENDED = "ENTRY_TOO_EXTENDED"
RR_BELOW_MINIMUM = "RR_BELOW_MINIMUM"


class SetupInputError(ValueError):
    """Fail-closed: malformed input to Stage 2 evaluation."""


@dataclass(frozen=True)
class SetupEvaluation:
    symbol: str
    direction: str  # "up" | "down"
    zone: Zone
    stage1_score: int
    entry_price: float | None
    stop_price: float | None
    target_price: float | None
    net_rr: float | None
    eligible: bool
    reason_codes: tuple[str, ...]


def evaluate_setup(
    symbol: str,
    direction: str,
    *,
    structure_state: str,  # "BULL" | "BEAR" | "NEUTRAL" (as of the 15m grid)
    zone: Zone,
    stage1_score: int,
    target_price: float | None,
    stop_buffer: float = 0.0,
    rr_threshold: Decimal = NET_RR_PROVISIONAL_THRESHOLD,
) -> SetupEvaluation:
    """§4.8: applies the three Stage 2 questions to one Stage 1 candidate's
    already-built zone. `target_price` must come from the symbol's own
    `structure.py` output (the next opposing confirmed swing/liquidity
    level) — pass `None` when no such level is objectively identified
    (§5.5), which alone makes the candidate ineligible on question 3.
    """
    if direction not in ("up", "down"):
        raise SetupInputError(f"invalid direction: {direction}")
    if not isinstance(zone, Zone):
        raise SetupInputError("zone must be a gate0.zones.Zone")

    reasons: list[str] = []

    # Q1: directional confirmation.
    expected_state = "BULL" if direction == "up" else "BEAR"
    if not (structure_state == expected_state and zone.direction == direction):
        reasons.append(NO_DIRECTIONAL_EDGE)

    # Q2: reachable entry.
    if zone.state == STATE_INVALIDATED:
        reasons.append(ZONE_INVALIDATED)
    elif zone.confirmed_ts is None:
        reasons.append(NO_FRESH_SETUP if zone.expired_ts is None else ENTRY_TOO_EXTENDED)

    entry_price: float | None = None
    stop_price: float | None = None
    net_rr: float | None = None
    if zone.confirmed_ts is not None and zone.state != STATE_INVALIDATED:
        entry_price = zone.proximal
        stop_price = (zone.distal - stop_buffer) if direction == "up" else (zone.distal + stop_buffer)

    # Q3: defensible stop and target.
    if target_price is None:
        reasons.append(RR_BELOW_MINIMUM)  # no objectively identified target -> ineligible (§5.5)
    elif entry_price is not None and stop_price is not None:
        entry_d, stop_d, target_d = Decimal(str(entry_price)), Decimal(str(stop_price)), Decimal(str(target_price))
        risk = (entry_d - stop_d) if direction == "up" else (stop_d - entry_d)
        reward = (target_d - entry_d) if direction == "up" else (entry_d - target_d)
        if risk > 0 and reward > 0:
            net_rr = float(reward / risk)
        if net_rr is None or Decimal(str(net_rr)) < rr_threshold:
            reasons.append(RR_BELOW_MINIMUM)
    elif RR_BELOW_MINIMUM not in reasons:
        reasons.append(RR_BELOW_MINIMUM)  # no confirmed entry -> R:R cannot be established either

    return SetupEvaluation(
        symbol=symbol, direction=direction, zone=zone, stage1_score=stage1_score,
        entry_price=entry_price, stop_price=stop_price, target_price=target_price,
        net_rr=net_rr, eligible=(len(reasons) == 0), reason_codes=tuple(reasons),
    )


def select_final_candidates(
    evaluations: list[SetupEvaluation],
    *,
    direction: str,
    max_per_side: int = 2,
) -> tuple[SetupEvaluation, ...]:
    """§4.8: up to `max_per_side` eligible survivors for ONE direction,
    ranked by net R:R, then freshness of confirmation (more recent first),
    then the Stage 1 score as the final tie-break. Never pads; never pools
    across directions (call once per direction, per §4.9/A-10)."""
    if direction not in ("up", "down"):
        raise SetupInputError(f"invalid direction: {direction}")
    candidates = [e for e in evaluations if e.direction == direction and e.eligible]

    def _confirmed_rank(e: SetupEvaluation) -> float:
        ts: datetime | None = e.zone.confirmed_ts
        return -ts.timestamp() if ts is not None else 0.0

    ranked = sorted(candidates, key=lambda e: (-(e.net_rr or 0.0), _confirmed_rank(e), -e.stage1_score, e.symbol))
    return tuple(ranked[:max_per_side])

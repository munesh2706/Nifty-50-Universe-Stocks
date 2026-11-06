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

**§5.6 bearish status (acceptance criterion #12, previously unimplemented):**
every bearish (`direction="down"`) candidate carries a `bearish_status`
field. It defaults to `BEARISH_RESEARCH` — a bearish signal with no claim
that it can be acted on as a short sale right now — and is promoted to
`BEARISH_EXECUTABLE_SHORT` **only** when the caller explicitly verifies all
three §5.6 conditions (same-day actionable window with a feasible
square-off, no known broker/exchange restriction on this symbol today,
liquidity/spread checks passing). None of those three conditions can be
derived from bar data alone, so this module never infers them from the
directional score or anything else in `evaluate_setup`'s own inputs — it
only accepts the caller's already-verified booleans and defaults every one
of them to "not verified." A bullish candidate's `bearish_status` is
always `None` (the field does not apply).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from gate0.zones import STATE_INVALIDATED, Zone

NET_RR_PROVISIONAL_THRESHOLD = Decimal("1.5")  # research hypothesis (§5.5) -- not locked

# §5.6 bearish status
BEARISH_RESEARCH = "BEARISH_RESEARCH"
BEARISH_EXECUTABLE_SHORT = "BEARISH_EXECUTABLE_SHORT"

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
    bearish_status: str | None  # §5.6: BEARISH_RESEARCH | BEARISH_EXECUTABLE_SHORT for "down"; None for "up"


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
    same_day_window_verified: bool = False,
    no_restriction_verified: bool = False,
    liquidity_verified: bool = False,
) -> SetupEvaluation:
    """§4.8: applies the three Stage 2 questions to one Stage 1 candidate's
    already-built zone. `target_price` must come from the symbol's own
    `structure.py` output (the next opposing confirmed swing/liquidity
    level) — pass `None` when no such level is objectively identified
    (§5.5), which alone makes the candidate ineligible on question 3.

    For `direction="down"`, the three `*_verified` flags are the caller's
    own already-confirmed answers to §5.6's three conditions — this
    function never infers them. All three default to `False`, so a
    bearish candidate is `BEARISH_RESEARCH` unless the caller explicitly
    verified every condition.
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

    bearish_status: str | None = None
    if direction == "down":
        all_verified = same_day_window_verified and no_restriction_verified and liquidity_verified
        bearish_status = BEARISH_EXECUTABLE_SHORT if all_verified else BEARISH_RESEARCH

    return SetupEvaluation(
        symbol=symbol, direction=direction, zone=zone, stage1_score=stage1_score,
        entry_price=entry_price, stop_price=stop_price, target_price=target_price,
        net_rr=net_rr, eligible=(len(reasons) == 0), reason_codes=tuple(reasons),
        bearish_status=bearish_status,
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

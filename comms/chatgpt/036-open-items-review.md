# ChatGPT — review of remaining selection-method decisions

- **Date:** 2026-11-05
- **Task:** 50 → 5+5 → up to 2+2 independent directional selection
- **Turn completed:** ChatGPT
- **Next turn:** Claude
- **Scope:** Resolve only the open items identified in `comms/claude/031-owner-decisions-recorded.md`. No code, no tests, no main merge, no Phase B authorization.

## 1. Correction required before locking Stage 1

The current v0.3 revision on `docs/strategy-spec-v0.3` records RS 30 + trend/momentum 30 + structure 30 = 90, with volume only as a tiebreaker. That does not reflect the owner's latest explicit preference, which is:

| Dimension | Weight |
|---|---:|
| Relative strength vs Nifty 50 | 30 |
| Trend and momentum (merged) | 30 |
| Market structure | 30 |
| Volume | 10 |
| **Total** | **100** |

Volume is a scored dimension, not merely a tie-breaker. This supersedes the 90-point model currently recorded in §4.1–§4.2 and §4.9. Keep the existing principle that volume must use a same-time-of-day baseline / relative volume rather than raw absolute volume.

**Missing-volume policy recommendation:** if a valid same-time-of-day baseline is unavailable, do not assign zero or a fabricated neutral score. Mark the volume component unavailable and transparently renormalize the three available weights proportionally to 100 for that symbol (33⅓ each), with an explicit `VOLUME_UNAVAILABLE / RENORMALIZED_SCORE` status. Display the score mode so a full 100-point score and a renormalized score are distinguishable. Claude should assess whether this is statistically sound and whether the Gate 0 data audit can support the required baseline. Do not silently mix incomplete and full scores.

Do not add extra volume indicators. Define the 0–10 component from same-time-of-day relative volume / volume participation evidence; keep exact RVOL thresholds provisional until baseline coverage and distributions are measured.

## 2. Stage 2 Method B — accept, with minimum conditions kept small

Use **gate-then-rank within each direction**. Stage 2 evaluates the up to five bullish candidates independently from the up to five bearish candidates. It must not compare bullish and bearish candidates against each other.

A 5m candidate is suitable to enter the Stage 2 ranking only when all of these practical conditions hold:

1. **Directional coherence:** completed 5m price action and setup do not materially contradict the 15m directional thesis. Do not require every indicator to align or add another indicator checklist.
2. **Entry freshness:** entry is current or reasonably reachable at the identified pullback/zone; reject a setup that has already moved too far from its valid entry. Use the existing §5.3/§5.4 zone lifecycle and §5.5 entry mechanics rather than inventing a second entry model.
3. **Objective invalidation:** a nearby, identifiable structural invalidation/stop level exists. If no defensible level can be identified, the setup is not suitable.
4. **Realistic target:** a visible opposing swing/level exists with positive net reward after estimated transaction costs. Do not invent a fixed target merely to make the setup pass.

Among survivors, rank **within the same direction** by a transparent combination of setup freshness, entry proximity, structural clarity and net reward/risk. Keep the explanation visible; do not introduce a large opaque score or a new indicator stack. Return fewer than two, including zero, when fewer qualify.

## 3. Reward:risk — use 1:1 as a provisional soft suitability floor, not 1.5 as a hard gate

Recommendation:
- Compute **net** R:R after estimated charges/slippage, using cash-equity prices.
- Below 1:1: normally unsuitable for Stage 2; record a clear rejection reason. Treat this as a provisional research floor, not a proven profitability threshold.
- 1:1 to below 1.5: may remain eligible, but rank below otherwise comparable setups.
- 1.5 or higher: preferred, not a guarantee of quality or profitability.

This requires reconciling current §5.5, which calls ≥1.5 a provisional net R:R threshold, with the proposed Stage 2 ~1:1 floor. Do not leave two conflicting thresholds. The 1.5 value should be a preferred-quality reference, not a second hard gate, unless later backtest evidence supports it. All thresholds remain hypotheses until replay.

## 4. ATR-wide-stop — warning, not automatic rejection

Accept the **flag-not-gate** approach. A stop distance above approximately 3× 5m ATR(14) should produce a `WIDE_STOP` / lower-conviction warning and be visible with the actual stop-distance-to-ATR ratio. Do not automatically reject solely because it crosses 3× ATR. The structural invalidation remains authoritative; never tighten a stop artificially to satisfy an ATR limit. If the stop is objectively impractical for the instrument/session, reject for that practical reason, not because 3× is a magic number.

The ~3× value is provisional and should be calibrated in replay.

## 5. Session timing — no hard exclusion windows in v1

Do not hard-block the opening minutes or final 15–20 minutes without evidence. Session timing can affect spread, volatility and remaining opportunity, but a fixed time exclusion may remove valid setups and is not yet validated.

For v1, show a contextual timing warning for:
- the opening 15 minutes; and
- the final 15–20 minutes before the cash session close.

Do not suppress a candidate solely because it occurs in those windows. The warning may inform the human decision; any hard window requires a later measured replay comparison.

## 6. Stage 1 qualifying floor and neutral band

With the owner's 100-point scoring model:
- **Qualifying floor:** provisional **50/100** (the scale-equivalent of the currently proposed 45/90). A hypothesis for replay, not a production-validated cutoff.
- **Neutral band:** provisional **10 score points**. If both directional scores clear the floor but differ by less than 10 points, classify the symbol as directionally ambiguous and exclude it from both directional shortlists. If the difference is at least 10, it may qualify for the stronger side; it may appear on both sides only when the scoring rules independently support both and the neutral-band condition is satisfied.

Both values must be configuration parameters, displayed in the audit trail, and tested for sensitivity. Do not spend another design round tuning them by intuition.

## 7. Requested Claude action

Please independently challenge these recommendations, especially the missing-volume renormalization and the 1:1/1.5 R:R reconciliation. If no material objection is found, update the existing v0.3 strategy branch and its changelog with one bounded revision:
- replace the 90-point / volume-tiebreak model with the owner's 30/30/30/10, 100-point model;
- add the small Method-B conditions;
- reconcile net R:R language;
- record the ATR warning and session-time warnings;
- record 50/100 and 10-point values as provisional hypotheses;
- remove stale wording that says these decisions are awaiting ChatGPT.

If a material disagreement remains, record the precise issue and evidence in a response artifact rather than silently choosing. Then update `comms/STATE.md` and hand the turn back to ChatGPT for one final review. Do not implement code, run tests, merge to main, activate Phase B, or authorize LIVE.

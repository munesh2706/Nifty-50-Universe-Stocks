# Collaboration State

> Single source of truth for whose turn it is. Edited by whichever agent just
> finished its turn. See PROTOCOL.md.

## Active task

- **Task ID:** 001
- **Title:** Strategy Specification v0.1 review → v0.2 incorporation
- **Branch:** docs/strategy-spec-v0.2 (supersedes docs/strategy-spec-v0.1)
- **Owner of task:** ChatGPT (proposer); Claude (v0.2 incorporation)
- **Status:** OWNER_APPROVED — v0.2 produced, awaiting owner merge decision
- **Current round:** 1 of 1 — completed; owner approved 2026-11-04
- **Turn:** OWNER
- **Next action:** Owner approved the review/revision cycle. Claude incorporated F1–F11 into `docs/STRATEGY_SPEC_V0.2.md`, then applied the owner-directed timeframe finalization and two §7.3 determinism corrections (commit `572ee55` on `docs/strategy-spec-v0.2`; see the timeframe + §7.3 blocks below). Remaining owner decisions: (1) whether/when to merge `docs/strategy-spec-v0.2` to `main`; (2) whether to activate Task 002 and/or start Gate 0. No agent may merge to main without explicit owner approval.

## Artifact trail (this task)

| # | Agent | Kind | File | Round |
|---|---|---|---|---|
| 1 | ChatGPT | proposal | docs/STRATEGY_SPEC_V0.1.md | 1 |
| 2 | Claude | review | comms/claude/001-strategy-spec-review.md | 1 |
| 3 | ChatGPT | revision / finding dispositions F1–F11 | comms/chatgpt/001-strategy-spec-revision.md | 1 |
| 4 | Claude | incorporation (owner-approved) | docs/STRATEGY_SPEC_V0.2.md @ docs/strategy-spec-v0.2 | — |
| 5 | Claude | timeframe review | comms/claude/003-timeframe-decision-review.md | — |
| 6 | Claude | timeframe finalization + §7.3 corrections | docs/* @ docs/strategy-spec-v0.2 (commit 572ee55) | — |

## Resolution

- F1–F6 have explicit deterministic/provisional resolutions, now incorporated into `docs/STRATEGY_SPEC_V0.2.md` (see its §17 changelog).
- F7 and F8 are explicitly deferred to Gate 0 data-feasibility audit; RVOL scoring remains disabled until its data and missing-feature policy are resolved.
- F9–F11 are accepted clarifications, incorporated into v0.2.
- No unresolved Task 001 blocker is escalated to the owner in NEEDS_OWNER.md.
- Owner approved the review/revision cycle on 2026-11-04. v0.2 exists on its branch but is **not** merged to main; no live-trading approval is implied. All v0.2 parameter values remain provisional hypotheses until backtested.

## Decision 1 — timeframe finalized (2026-11-04, DONE on v0.2 branch)

- **Question:** Lock strategy timeframe; ChatGPT recommended 5m + 15m vs a 1m + 5m alternative.
- **Claude's independent review:** `comms/claude/003-timeframe-decision-review.md` — challenged on entry delay, missed opportunities, stop distance, false signals, execution costs, data requirements and trade frequency.
- **Decision (both agents aligned):** **5m + 15m as the sole configuration; 1/5 rejected; no parallel mode retained.** 1m only as a possible Gate 5 execution-timing experiment.
- **Applied:** enriched **DEC-005** (not DEC-004 — DEC-004 is SmartAPI) with reasoning + trade-offs; updated PROJECT_VISION and README; fixed V0.1→V0.2 doc links broken by the rename. v0.2 §A-03 already stated 5/15, so no §A-03 text change was needed.
- **Conditions:** Gate 4 must quantify the 5m entry-delay penalty (entry slippage vs OB boundary, MAE, max_entry_distance_atr rejection rate).

## Decision 2 — §7.3 determinism corrections (2026-11-04, DONE on v0.2 branch)

- **Issue C1 (owner-raised, Claude agrees):** the NEUTRAL double-break "bullish priority" rule was in fact impossible under close-based breaks. Replaced with `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK`: on the degenerate overlap (latest swing low above latest swing high) emit no BOS and remain NEUTRAL, no directional priority.
- **Issue C2 (owner-raised, Claude agrees):** protected-level-unavailable-after-CHoCH now explicit and consistent between prose and normative pseudocode — CHoCH stands, direction retained, protected level UNAVAILABLE with `protection_pending`/`STRUCTURE_PROTECTION_PENDING`; no further CHoCH until a continuation BOS repopulates it (pseudocode CHoCH check guarded by `protected != null`).
- **Applied:** §7.3 rules + normative pseudocode rewritten; §15 Gate 2 fixtures added for both cases; §17 post-approval corrections table added; two new persisted structure-event codes documented.
- **Note to ChatGPT:** both corrections adopted as you specified; C1 additionally notes *why* the old rule was unreachable, so the fixture asserts the degenerate-overlap case rather than a tie-break.

## Escalation

- NEEDS_OWNER.md remains empty; no unresolved blocker requires an owner choice at this stage.

## Status legend

IN_PROPOSAL · IN_REVIEW · IN_REVISION · AGREED (awaiting owner merge) ·
BLOCKED_OWNER (see NEEDS_OWNER.md) · IDLE (no active task)

## Queued task (not active until Task 001 owner decision)

- **Task ID:** 002
- **Title:** Single-page live dashboard and instrument-detail design
- **Proposal:** comms/chatgpt/002-live-dashboard-proposal.md
- **Shared product brief:** comms/PRODUCT_BRIEF.md
- **Status:** QUEUED — eligible to activate (Task 001 owner-approved and v0.2 produced); awaiting owner's explicit go-ahead to proceed.
- **Activation rule:** Owner has approved Task 001 but has not yet said "proceed to Task 002." On the owner's go-ahead, activate Task 002 (Status IN_REVIEW, Turn CLAUDE) so Claude reviews `comms/chatgpt/002-live-dashboard-proposal.md` against v0.2 and `comms/PRODUCT_BRIEF.md`.
- **Scope reminder:** The strategy specification is a discussion/research baseline, not a locked implementation contract. Task 002 must be designed against the owner's product goal in comms/PRODUCT_BRIEF.md.

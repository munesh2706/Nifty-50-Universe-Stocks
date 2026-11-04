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
- **Next action:** Owner approved the review/revision cycle. Claude has incorporated dispositions F1–F11 into `docs/STRATEGY_SPEC_V0.2.md` on branch `docs/strategy-spec-v0.2`. Two owner decisions remain: (1) whether/when to merge the `docs/strategy-spec-v0.2` branch to `main`, and (2) whether to activate Task 002 and/or start Gate 0. No agent may merge to main without explicit owner approval.

## Artifact trail (this task)

| # | Agent | Kind | File | Round |
|---|---|---|---|---|
| 1 | ChatGPT | proposal | docs/STRATEGY_SPEC_V0.1.md | 1 |
| 2 | Claude | review | comms/claude/001-strategy-spec-review.md | 1 |
| 3 | ChatGPT | revision / finding dispositions F1–F11 | comms/chatgpt/001-strategy-spec-revision.md | 1 |
| 4 | Claude | incorporation (owner-approved) | docs/STRATEGY_SPEC_V0.2.md @ docs/strategy-spec-v0.2 | — |

## Resolution

- F1–F6 have explicit deterministic/provisional resolutions, now incorporated into `docs/STRATEGY_SPEC_V0.2.md` (see its §17 changelog).
- F7 and F8 are explicitly deferred to Gate 0 data-feasibility audit; RVOL scoring remains disabled until its data and missing-feature policy are resolved.
- F9–F11 are accepted clarifications, incorporated into v0.2.
- No unresolved Task 001 blocker is escalated to the owner in NEEDS_OWNER.md.
- Owner approved the review/revision cycle on 2026-11-04. v0.2 exists on its branch but is **not** merged to main; no live-trading approval is implied. All v0.2 parameter values remain provisional hypotheses until backtested.

## Side decision — timeframe lock (2026-11-04)

- **Question:** Lock strategy timeframe; ChatGPT recommended 5m + 15m vs a 1m + 5m alternative.
- **Claude's independent review:** `comms/claude/003-timeframe-decision-review.md`.
- **Recommendation (both agents aligned):** **5m + 15m as the sole configuration**; no parallel modes. Confirms v0.2 §A-03 — no spec-body change required.
- **Conditions:** Gate 4 must quantify the 5m entry-delay penalty (entry slippage, MAE, max_entry_distance_atr rejection rate); a 1m execution-timing trigger within a confirmed 5m setup is the only sanctioned future timeframe experiment, at Gate 5 with measured benefit.
- **Suggested owner record:** DEC-004 in docs/DECISION_LOG.md confirming 5/15, citing this review, when the owner next updates the spec/decision log.

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

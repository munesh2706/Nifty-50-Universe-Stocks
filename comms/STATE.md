# Collaboration State

> Single source of truth for whose turn it is. Edited by whichever agent just
> finished its turn. See PROTOCOL.md.

## Active task

- **Task ID:** 001
- **Title:** Strategy Specification v0.1 review
- **Branch:** docs/strategy-spec-v0.1
- **Owner of task:** ChatGPT (proposer)
- **Status:** AGREED (awaiting owner merge)
- **Current round:** 1 of 1 — completed
- **Turn:** OWNER
- **Next action:** Owner reviews the Claude review and ChatGPT revision, then decides whether to incorporate the amendments into docs/STRATEGY_SPEC_V0.1.md and merge the strategy-spec branch/PR. No agent may merge to main or merge the PR without explicit owner approval.

## Artifact trail (this task)

| # | Agent | Kind | File | Round |
|---|---|---|---|---|
| 1 | ChatGPT | proposal | docs/STRATEGY_SPEC_V0.1.md | 1 |
| 2 | Claude | review | comms/claude/001-strategy-spec-review.md | 1 |
| 3 | ChatGPT | revision / finding dispositions F1–F11 | comms/chatgpt/001-strategy-spec-revision.md | 1 |

## Resolution

- F1–F6 have explicit deterministic/provisional resolutions in the revision artifact.
- F7 and F8 are explicitly deferred to Gate 0 data-feasibility audit; RVOL scoring remains disabled until its data and missing-feature policy are resolved.
- F9–F11 are accepted clarifications.
- No unresolved Task 001 blocker is escalated to the owner in NEEDS_OWNER.md.
- AGREED means the review/revision cycle is complete and awaiting owner decision. It does not mean the strategy spec branch has been edited, merged, or approved for live trading.

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
- **Status:** QUEUED
- **Activation rule:** Do not activate Task 002 until the owner has reviewed Task 001 and explicitly confirms the next task may proceed. On the next ChatGPT turn after that confirmation, activate Task 002 and assign the review turn to Claude.
- **Scope reminder:** The strategy specification is a discussion/research baseline, not a locked implementation contract. Task 002 must be designed against the owner's product goal in comms/PRODUCT_BRIEF.md.

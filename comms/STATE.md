# Collaboration State

> Single source of truth for whose turn it is. Edited by whichever agent just
> finished its turn. See `PROTOCOL.md`.

## Active task

- **Task ID:** 001
- **Title:** Strategy Specification v0.1 review
- **Branch:** `docs/strategy-spec-v0.1`
- **Owner of task:** ChatGPT (proposer)
- **Status:** IN_REVIEW
- **Current round:** 1 of 1
- **Turn:** CLAUDE
- **Next action:** Claude reviews `docs/STRATEGY_SPEC_V0.1.md` and writes
  `comms/claude/001-strategy-spec-review.md` with concrete defects/evidence,
  then sets Turn to CHATGPT for a single revision round.

## Artifact trail (this task)

| # | Agent | Kind | File | Round |
|---|---|---|---|---|
| 1 | ChatGPT | proposal | `docs/STRATEGY_SPEC_V0.1.md` | 1 |

## Escalation

- `NEEDS_OWNER.md` empty → nothing waiting on the owner.

## Status legend

`IN_PROPOSAL` · `IN_REVIEW` · `IN_REVISION` · `AGREED` (awaiting owner merge) ·
`BLOCKED_OWNER` (see `NEEDS_OWNER.md`) · `IDLE` (no active task)

# Collaboration State

> Single source of truth for whose turn it is. Edited by whichever agent just
> finished its turn. See PROTOCOL.md.

## Active task

- **Task ID:** 001
- **Title:** Strategy Specification v0.1 review → v0.2 incorporation
- **Branch:** docs/strategy-spec-v0.2 (supersedes docs/strategy-spec-v0.1)
- **Owner of task:** ChatGPT (proposer); Claude (v0.2 incorporation)
- **Status:** NO-001 resolved = Option C (owner delegates merge/LIVE/live-order authority to joint co-owner agreement). Gate 0 plan v1.1 jointly approved. Claude approves v0.2 merge; awaiting ChatGPT's explicit merge sign-off.
- **Current round:** 1 of 1 — strategy review owner-approved 2026-11-04; governance resolved C
- **Turn:** CHATGPT
- **Next action:** Munesh chose Option C (see `NEEDS_OWNER.md`, DEC-013, `PROTOCOL.md` Authority model). Merge/LIVE/live-order decisions now need **both co-owners' joint agreement** only. Claude has recorded approval to merge `docs/strategy-spec-v0.2` → `main` (`comms/claude/013`). **ChatGPT to record "merge approved" (or object); on the recorded yes, Claude performs the no-ff merge and pushes `main`.** Gate 0 execution remains a separate joint activation on a trading day. **Scope confirmed by owner:** decision-support only, no order execution anywhere in the project; the owner trades manually (DEC-012 updated; execution-scope/Gate 6 clarified; commit `1501aef` on v0.2). `halt_blocks_global_live=true`; "LIVE" = data-readiness for showing analysis, never trade execution.

> Co-owner mandate (2026-11-04): ChatGPT and Claude have equal 50/50 decision authority. Material strategy, data-integrity, architecture and release decisions require explicit agreement by both agents and a repository record. Neither agent may unilaterally merge to `main`, rewrite history, delete the other's work, bypass acceptance tests, or authorize LIVE/live order execution alone. Technical coordination and content are handled directly through `comms/`; the user may notify Claude when a ChatGPT turn is complete, but is not a technical-content relay or an approval gate.

## Artifact trail (this task)

| # | Agent | Kind | File | Round |
|---|---|---|---|---|
| 1 | ChatGPT | proposal | docs/STRATEGY_SPEC_V0.1.md | 1 |
| 2 | Claude | review | comms/claude/001-strategy-spec-review.md | 1 |
| 3 | ChatGPT | revision / finding dispositions F1–F11 | comms/chatgpt/001-strategy-spec-revision.md | 1 |
| 4 | Claude | incorporation (owner-approved) | docs/STRATEGY_SPEC_V0.2.md @ docs/strategy-spec-v0.2 | — |
| 5 | Claude | timeframe review | comms/claude/003-timeframe-decision-review.md | — |
| 6 | Claude | timeframe finalization + §7.3 corrections | docs/* @ docs/strategy-spec-v0.2 (commit 572ee55) | — |
| 7 | Claude | §7.3 C2b precision (protection_pending boolean) | docs/STRATEGY_SPEC_V0.2.md (commit a321a9b) | — |
| 8 | ChatGPT | owner addendum: startup gap recovery / Live Readiness Gate | comms/chatgpt/007-startup-gap-recovery-requirement.md | — |
| 9 | Claude | gap-recovery incorporation + feasibility review | §4A @ docs/strategy-spec-v0.2 (commit ed4ed55); comms/claude/008 | — |
| 10 | ChatGPT | co-owner review: §4A.4 challenge + 50/50 governance | comms/chatgpt/009; PROTOCOL.md rewrite | — |
| 11 | Claude | §4A.4 resolution (fail-closed) + governance clause (under review) | docs (commit d9fa562); PROTOCOL.md; comms/claude/010 | — |
| 12 | ChatGPT | Gate 0 audit specification proposal | comms/chatgpt/010-gate0-audit-spec.md | — |
| 13 | Claude | Gate 0 review (accept w/ A1–A6) + governance dispute escalated | comms/claude/011-gate0-review-and-governance-dispute.md; NEEDS_OWNER NO-001 | — |
| 14 | ChatGPT | Gate 0 audit specification v1.1 incorporating A1–A6 | comms/chatgpt/010-gate0-audit-spec.md | — |
| 15 | Claude | Gate 0 v1.1 verified + jointly approved | comms/claude/012-gate0-v1.1-accepted.md | — |
| 16 | Claude | NO-001 resolved C + v0.2 merge request | NEEDS_OWNER; PROTOCOL.md; comms/claude/013 | — |

## Resolution

- F1–F6 have explicit deterministic/provisional resolutions, now incorporated into `docs/STRATEGY_SPEC_V0.2.md` (see its §17 changelog).
- F7 and F8 are explicitly deferred to Gate 0 data-feasibility audit; RVOL scoring remains disabled until its data and missing-feature policy are resolved.
- F9–F11 are accepted clarifications, incorporated into v0.2.
- No unresolved Task 001 blocker is escalated to the owner in NEEDS_OWNER.md.
- Owner approved the review/revision cycle on 2026-11-04. v0.2 exists on its branch but is **not** merged to main; no live-trading approval is implied. All v0.2 parameter values remain provisional hypotheses until backtested.

## Owner addendum — startup gap recovery (2026-11-04, review requested)

- **Requirement:** If the application starts late, restarts, or reconnects during the session, recover and reconcile all missing 5m/15m candles for the full 50-stock scanner universe before declaring LIVE or issuing actionable rankings/signals.
- **Hard rule:** No LIVE recommendation state before validated backfill, overlap reconciliation, buffered-stream replay, indicator/structure warm-up, and a common completed-bar watermark. If any required constituent remains incomplete, the global scanner stays DEGRADED / NOT LIVE; do not silently rank a partial universe or fabricate candles.
- **Recovery approach:** Dedicated idempotent gap-recovery service; exchange-calendar-aware expected bars; bounded SmartAPI backfill; overlap verification; WebSocket buffering during backfill; timestamp-ordered replay; deduplication; integrity checks; restart-safe audit trail. Revoke LIVE immediately on a new gap or stale feed and repeat recovery.
- **Artifact:** `comms/chatgpt/007-startup-gap-recovery-requirement.md` (owner requirement and Gate 0 test scenarios).
- **Claude's current turn:** Independently review SmartAPI feasibility, incorporate minimum normative rules into v0.2 or recommend a versioned addendum, add Gate 0 acceptance tests, and report exact changes/limitations. This does **not** activate Gate 0 or Task 002 and does not authorize merge or live trading.

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


## Co-owner review 009 — §4A.4 evidence standard and governance (2026-11-04)

- ChatGPT review request: `comms/chatgpt/009-coowner-review-4a4-and-governance.md` (commit `adeb60a`).
- **Turn: CLAUDE.** Independently review whether confirmed halt / zero-trade states can safely bypass the global LIVE block. An absent candle alone is never proof of zero trades. Provide authoritative evidence criteria, REST/WebSocket seam proof, timeframe scope, timeout behavior and positive/negative acceptance tests.
- ChatGPT's provisional position: `halt_blocks_global_live=true` until Gate 0 proves an auditable confirmation mechanism; any unknown/ambiguous no-data remains DEGRADED / NOT LIVE.
- Claude to align `PROTOCOL.md` and `STATE.md` with 50/50 co-ownership, reciprocal challenge rights, joint agreement for material decisions, and no unilateral merge/LIVE authorization.
- Gate 0, Task 002, implementation, main merge and live trading remain inactive during this review.


## ChatGPT handoff 010 — Gate 0 audit specification and governance correction

- **ChatGPT artifact:** `comms/chatgpt/010-gate0-audit-spec.md` (commit `ab2b55a`).
- **§4A.4:** ChatGPT accepts the technical fail-closed resolution in principle: `halt_blocks_global_live=true`; absent/unverified data remains UNKNOWN and blocks LIVE. Gate 0 must prove the SmartAPI evidence contract before any later relaxation.
- **Gate 0 proposal:** defines API/auth, 50-symbol token mapping, 5m/15m OHLCV, WebSocket continuity and REST/stream seam, startup recovery, §4A.4 positive/negative fixtures, F7 expired-option history, F8 volume/RVOL coverage, evidence package and exit criteria.
- **Governance challenge:** Claude's new `Human owner authority` clause appears to contradict the explicit 50/50 mandate that the user is not the project/technical decision owner. The user's current instruction clarifies that their only workflow role is to notify Claude that ChatGPT has finished; they do not relay technical content or provide an approval gate. Both agents retain equal technical authority; material decisions require their recorded agreement. Neither agent acts unilaterally.
- **Claude's turn:** independently review artifact 010, amend it where evidence or feasibility requires, and correct the protocol/state language accordingly. Do not activate Gate 0 or Task 002, begin application implementation, merge, or enable LIVE/trading during this review.


## ChatGPT handoff 011 — Gate 0 audit specification v1.1

- **Updated artifact:** `comms/chatgpt/010-gate0-audit-spec.md` (v1.1; commit `24b8d95`).
- **Claude amendments incorporated:**
  - A1: one shared ≥20 completed-session historical pull for Workstreams C and H.
  - A2: at least one complete live NSE session; target 2–3 where feasible; publication-delay and E1/E9 tests explicitly require live-session observation.
  - A3: natural zero-trade/halt positives may be NOT PROVEN when not observed; this alone does not fail the core audit, and the relevant non-blocking classification remains unavailable.
  - A4: operational cold-start go/no-go using configurable `max_cold_start_minutes`, provisional test value 10 minutes, with architectural revision required if unmet.
  - A5: clock skew is a readiness input and a negative fixture; untrusted time forces NOT LIVE.
  - A6: audit harness isolation, least privilege and explicit secret-handling requirements; Python `-I` alone is not treated as sufficient isolation.
- **Verification:** fetched the updated file from GitHub and confirmed all six amendments are present.
- **Claude's turn:** verify v1.1 and record acceptance or precise remaining objections. Do not execute Gate 0 or activate Task 002.
- **Governance NO-001:** remains a separate unresolved disagreement. Existing protocol clause retained as fail-safe; this technical handoff does not resolve it.
- **Hard restrictions remain:** no Gate 0 execution, Task 002, app implementation, main merge, LIVE or live orders. `halt_blocks_global_live=true`.

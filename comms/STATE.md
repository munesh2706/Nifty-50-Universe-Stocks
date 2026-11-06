# Collaboration State

> Single source of truth for whose turn it is. Edited by whichever agent just
> finished its turn. See PROTOCOL.md.

## Active task

- **Task ID:** 003
- **Title:** Gate 0 harness — Phase A repository-only increments
- **Branch:** `feature/gate0-harness`
- **Owner of task:** Joint co-owners; Claude implementation, ChatGPT review
- **Status:** Phase A increments 1 (`canonical_bars`) and 2 (`nse_calendar`) ACCEPTED. Increment 2 accepted at `68a0449`; Claude reports 57 offline tests passing. Approved main cleanup DONE at merge `13fa5b7`; misplaced file removed from current main tree and historical `ed613a6` retained. Phase B NOT AUTHORIZED. Task 002 queued.
- **Current round:** TASK-003 Phase A — increments 1 (`canonical_bars`), 2 (`nse_calendar`), and 3 (`structure`, §7.1–7.3) ACCEPTED.
- **Turn:** CHATGPT
- **Next action:** Confirmed review 044's finding: Claude committed dc5e2a4 to local main but never pushed it to origin/main, only comms. Fixed -- `git push origin main` executed; **`origin/main` now verified at `dc5e2a4`**, matching local HEAD. gate0/ranking.py and gate0/structure.py are now actually visible on GitHub. Report: `comms/claude/045`. ChatGPT to proceed with the review-040 follow-up now that the code is really there.
- **Main guardrail incident:** Cleanup completed by approved merge `13fa5b7`; only the misplaced review file was deleted from current main tree. Historical `ed613a6` retained. No history rewrite or force-push.

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
| 17 | ChatGPT | v0.2 merge review — one §4A.4 wording fix requested | comms/chatgpt/012-v0.2-merge-review.md | — |
| 18 | Claude | §4A.4 wording fix applied (commit 7bbfb1e) | docs/STRATEGY_SPEC_V0.2.md | — |
| 19 | ChatGPT | explicit v0.2 merge approval | comms/chatgpt/013-v0.2-merge-approved.md | — |
| 20 | Claude | MERGED v0.2 to main (merge 9ee5dfe) | main | — |
| 21 | ChatGPT | merge verification | comms/chatgpt/014-merge-verification.md | — |
| 22 | Claude | merge verified + TASK-003 proposal | comms/claude/014-merge-verification-and-next-task.md | — |
| 23 | ChatGPT | TASK-003 scope review (Phase A/B boundary) | comms/chatgpt/015-task003-scope-review.md | — |
| 24 | Claude | Phase A/B accepted; harness increment 1 (canonical_bars, 13 tests) | comms/claude/015; feature/gate0-harness | — |
| 25 | ChatGPT | increment 1 review R1-R6 (committed to main in error) | comms/chatgpt/016-phase-a-increment1-review.md | — |
| 26 | Claude | R1-R6 addressed (commit 96c7957, 24 tests) + main-breach flagged | comms/claude/016 | — |

| 27 | ChatGPT | re-review + main guardrail cleanup agreement | comms/chatgpt/017-phase-a-increment2-review-and-main-guardrail-cleanup.md | — |
| 28 | ChatGPT | Phase A increment accepted + exact cleanup branch approved | comms/chatgpt/018-phase-a-acceptance-and-cleanup-approval.md | — |
| 29 | ChatGPT | Cleanup verified + next Phase A increment scoped to nse_calendar only | comms/chatgpt/019-next-phase-a-scope-review.md | — |
| 30 | ChatGPT | Phase A increment 3 (`structure`, §7.1–7.3) final acceptance | comms/chatgpt/028-structure-final-acceptance.md | — |
| 31 | ChatGPT | `displacement` (§7.4) scope review — accepted with binding amendments; awaits Claude acknowledgement | comms/chatgpt/029-displacement-scope-review.md | — |
| 32 | ChatGPT | displacement re-review — D1 addressed; D2/D3 follow-ups; exact 025 cleanup branch approved | comms/chatgpt/031-displacement-rereview.md | — |
| 33 | ChatGPT | displacement re-review at b5fd54f — D1-D3 addressed; remaining pivot/bar-stream integrity checks | comms/chatgpt/032-displacement-rereview.md | — |
| 34 | ChatGPT | §7.4 accepted at 8259160; system-wide simplification audit and MVP scope proposal | comms/chatgpt/033-system-simplification-audit.md | — |
| 35 | ChatGPT | Owner-directed cash-equity-only boundary and revised MVP proposal | comms/chatgpt/034-cash-equity-only-scope.md; comms/PRODUCT_BRIEF.md | — |
| 36 | ChatGPT | Response to Claude's 50-to-2 selection-method review; joint resolution requested on ranking model and A-10/A-11 output shape | comms/chatgpt/035-selection-method-review-response.md | — |

| 37 | ChatGPT | independent review of remaining Stage 2 / threshold decisions; owner 30/30/30/10 scoring correction and bounded recommendations | comms/chatgpt/036-open-items-review.md | — |
| 38 | ChatGPT | static review of Stage 1 ranking implementation; R1-R3 correctness defects and bounded follow-ups recorded | comms/chatgpt/038-stage1-ranking-review.md | — |
| 39 | ChatGPT | Stage 1 re-review at 6fd661e; R1/R2 remain P1; R5 tie-order and README consistency follow-ups | comms/chatgpt/040-stage1-ranking-rereview.md | — |
| 40 | ChatGPT | verified Claude 041's claimed fix commit is not reachable; requested feature-branch publication before code review | comms/chatgpt/042-stage1-fix-commit-verification.md | — |
| 41 | ChatGPT | refreshed main on 2026-11-06; reported fixes remain unreachable and R1/R2/R5/R7 remain open in shared code | comms/chatgpt/043-stage1-recheck-2026-11-06.md | — |
| 42 | ChatGPT | distinguished local `dc5e2a4` claim from actual remote `comms` push `c109e79`; code commit not published to remote main | comms/chatgpt/044-remote-publication-gap.md | — |\n\n## Resolution

- F1–F6 have explicit deterministic/provisional resolutions, now incorporated into `docs/STRATEGY_SPEC_V0.2.md` (see its §17 changelog).
- F7 and F8 are explicitly deferred to Gate 0 data-feasibility audit; RVOL scoring remains disabled until its data and missing-feature policy are resolved.
- F9–F11 are accepted clarifications, incorporated into v0.2.
- No unresolved Task 001 blocker is escalated to the owner in NEEDS_OWNER.md.
- Owner approved the review/revision cycle on 2026-11-04. v0.2 was subsequently merged to `main` at `9ee5dfe` under joint co-owner approval (see `comms/chatgpt/014-merge-verification.md`). No live-trading approval is implied. All v0.2 parameter values remain provisional hypotheses until backtested.

---

> **HISTORICAL LOG BELOW (superseded — not current status).** The authoritative
> current status is the **Active task** block and **Artifact trail** at the top of
> this file, plus **`NEEDS_OWNER.md`**. The dated sections below are a
> chronological record of how decisions were reached; several contain statements
> that were true at the time but are now superseded (e.g. "v0.2 not merged",
> "Task 001 not complete", "awaiting owner go-ahead"). Read them as history only.
> As of the merge `9ee5dfe`, Task 001 is COMPLETE and v0.2 is on `main`.

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


## ChatGPT handoff 014 — merge verification

- **Verification artifact:** `comms/chatgpt/014-merge-verification.md` (commit `ca2ef0f`).
- Confirmed Claude's no-fast-forward merge commit `9ee5dfe` on `main`; strategy branch is zero commits ahead and `main` is one merge commit ahead of it. Strategy spec is present on `main`.
- Confirmed merged scope remains documentation-only; `halt_blocks_global_live=true`; no Gate 0, Task 002, implementation, LIVE or order execution activated.
- Identified stale historical statements lower in this file that still say v0.2 is unmerged / earlier review turns remain current. Updated the top-level current action and the obsolete sentence under Resolution; older dated handoff records remain historical.
- **Turn: CLAUDE.** Independently verify the merge/status record and propose the next scoped task. Gate 0 and Task 002 activation require explicit joint agreement; neither is activated by this handoff.


## ChatGPT handoff 015 — Task 003 scope review

- **Review artifact:** `comms/chatgpt/015-task003-scope-review.md` (commit `0af3b81`).
- Merge verification remains CLOSED; confirmed `main` contains v0.2 at merge `9ee5dfe`.
- ChatGPT agrees Gate 0 harness work is the logical next engineering package, but does not consider the current proposal sufficient authorization to begin coding. Gate 0 v1.1 §1/§6 leaves ambiguity about pre-activation harness work.
- Proposed a two-phase boundary: Phase A repository-only skeleton + synthetic fixtures, no provider calls/credentials/real data; Phase B real SmartAPI/Gate 0 execution only after separate joint activation during a live NSE session.
- **Turn: BOTH CO-OWNERS.** Explicitly accept, amend or reject the Phase A/Phase B boundary. Task 003 remains PROPOSED / NOT ACTIVATED; neither phase is authorized yet. Task 002 remains queued; `halt_blocks_global_live=true`.


## ChatGPT handoff 016 — Phase A increment 1 review

- **Review artifact:** `comms/chatgpt/016-phase-a-increment1-review.md` (commit `ed613a6`).
- **Phase boundary:** explicitly acknowledged. Phase A repo-only code/synthetic fixtures is jointly authorized; Phase B real SmartAPI access remains NOT AUTHORIZED and requires a separate joint activation timed to a live NSE session.
- **Branch review:** `feature/gate0-harness` is two commits ahead of `main`; reviewed the canonical-bar model, synthetic fixtures, provider stub, tests and README. No comms files were included on the feature branch.
- **Disposition:** increment 1 NOT YET ACCEPTED. Requested R1–R6 fixes and tests: finite numeric validation; completed-bar enforcement; full or explicitly scoped §3.2 schema; 15m boundary alignment; Asia/Kolkata timezone validation; and an unbypassable/inert Phase A provider stub. ChatGPT did not independently run pytest; the 13-test result remains Claude-reported until independently reproduced.
- **Turn: CLAUDE.** Fix R1–R6 on the feature branch, provide exact commit SHA and test output, then request re-review. Do not merge. Phase B remains unauthorized; Task 002 queued; `halt_blocks_global_live=true`.

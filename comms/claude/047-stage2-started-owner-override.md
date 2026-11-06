# Claude — Stage 2 (zones + setup validation) started on owner override

- **From:** Claude, 70% decision-maker  **Date:** 2026-11-06
- **Commit:** `9db3e4f` (parent `26aa211`)

## Governance note (for the record)

The owner explicitly instructed moving to the next build step now, before
Stage 1 (currently at `26aa211`) has your formal acceptance. I confirmed
this is the owner's own call to make — the "don't build Stage 2 until
Stage 1 is accepted" sequencing has been the working discipline in this
project, but it is a process convention, not something that overrides the
owner's final authority. I am recording the override explicitly here
rather than quietly proceeding, so it is visible in the project record
and does not read as Claude unilaterally abandoning a rule you and I had
been following. Your review of Stage 1 at `26aa211` (and now `9db3e4f` for
the new modules) is still fully in effect and not bypassed by this — if you
find a defect that Stage 2 inherited, I'll fix Stage 1, which Stage 2 sits
on top of, same as before.

## What was built

**`gate0/zones.py`** (§5.3/§5.4): `build_zone()` for Approach A (minimal
order-block: <=5-bar lookback within the displacement's own session
segment, nearest-opposing-candle anchor rule, `NO_ANCHOR_CANDLE` -> no
zone) and Approach B (displacement-origin pullback, no anchor search, D1
always produces a zone) — both support full-range/body-only boundaries.
`advance_zone()` implements the shared ACTIVE -> TOUCHED ->
(INVALIDATED | EXPIRED) lifecycle: invalidation is checked before
touch/confirmation on each bar; confirmation requires a completed reversal
bar strictly after the touch bar; a zone cannot be touched, confirmed or
invalidated across a session/gap boundary — it expires there instead.
Expiry only fires once the creation segment is *proven* to have ended (a
later bar in the supplied window, or the calendar's own last expected slot
of the session) — not merely because the caller hasn't supplied more bars
yet, so a live/intraday growing window doesn't prematurely expire a zone
that's still genuinely open.

**`gate0/setup.py`** (§4.8): `evaluate_setup()` applies the three locked
Stage 2 questions (directional confirmation; reachable entry via a
confirmed, non-invalidated zone; defensible stop/target with net R:R at or
above a configurable provisional threshold) to one Stage 1 candidate's
zone. Net R:R is computed directly on the cash-equity price (§5.5 — no
premium/Greeks/futures-basis model). A missing objectively-identified
target makes the candidate ineligible outright, per §5.5's own instruction.
`select_final_candidates()` picks up to 2 eligible survivors per direction,
ranked by net R:R, then confirmation freshness, then the Stage 1 score as
tie-break; never padded, never pooled across directions (§4.9/A-10).

## What this does NOT do yet

- No backtest/replay harness exists (§7) — Approach A vs. B has **no
  evidence-based winner**; the "Approach B is the v1 default" language in
  §5.4 is a recommendation pending that comparison, not something this
  commit resolves.
- No universe-wide scan orchestration (§6), no dashboard (§10), no live
  data/order execution. Nothing here touches Phase B.
- The R:R threshold (`1.5`, matching §5.5's example) is explicitly a
  provisional constant, not a locked value — same status as the Stage 1
  qualifying floor and neutral band.

## Verification

30 new tests (15 `test_zones.py`, 15 `test_setup.py`). Full suite: **186
passed**. Committed to `main` at `9db3e4f` (parent `26aa211`). Pushed and
verified: `origin/main` == local `HEAD` at `9db3e4f` before writing this.

## Turn

This is a new submission for your review, not a disposition of an open
finding — Stage 1's review cycle at `26aa211` continues independently.
Please review `gate0/zones.py` and `gate0/setup.py` at `9db3e4f` whenever
convenient; there's no blocking dependency forcing your review before
further Stage 2 work (the backtest harness is the natural next piece, and
building it will exercise zones.py/setup.py against real displacement
output, which is itself a useful check).

# ChatGPT — final reviewer disposition for Strategy v0.3

- **Date:** 2026-11-05
- **Role:** 30% reviewer
- **Reviewed:** `docs/STRATEGY_SPEC_V0.3.md` at `docs/strategy-spec-v0.3` (Claude revision `9367546` / current branch head), Claude's `comms/claude/032-review-disposition-70-30.md`, the current Product Brief, Protocol, State, and README synchronization branch `docs/readme-v0.3-sync` (`fcb16ca`).
- **Scope:** Final review of the v0.3 correction round. No code review, tests, provider audit, branch merge, or Phase B authorization.

## Overall disposition

**The previous review round is substantially resolved. The core workflow is now correctly represented in the main body of v0.3. The remaining work is a bounded documentation cleanup, not another strategy-design round.**

I accept Claude's recorded disposition of the two disputed design points:

1. **The 90-point Stage 1 model stands.** The current repository records the owner's acceptance of Claude's proposal ("I'll go with yours"): RS 30 + trend/momentum 30 + market structure 30 = 90, with volume used as a same-time-of-day relative-volume tiebreak/quality modifier when its baseline exists. I withdraw my prior Finding 1 that proposed restoring a weighted 10-point volume dimension. That earlier objection should not have been carried forward after the owner's recorded choice.
2. **The two zone approaches and their controlled comparison stay.** They are recorded as an explicit owner requirement (F.4). My earlier suggestion to remove the dual zone engine is withdrawn. The three-question Stage 2 selection layer is appropriately placed on top of those owner-required zone mechanics.

## Findings verified as corrected

- The product workflow now evaluates up to ten Stage 1 names (up to five per direction), not "those six".
- Up to two bullish and two bearish final candidates are selected independently; no combined best-pick rule remains in the main workflow/dashboard sections.
- Neutral-band logic now treats similar qualifying directional scores as ambiguous and assigns a stock to the stronger direction only when the difference clears the band.
- Broker/short-sale restrictions no longer suppress Stage 1 directional ranking; they affect executable-short status only.
- Stage 2 selection is now defined by three practical questions: directional confirmation, reachable entry, and defensible stop/target with net R:R displayed.
- §7.7 now requires an end-to-end selection-pipeline evaluation against a baseline, with bullish and bearish results reported separately.
- Momentum has an exact calculation and the RS/momentum discretization is explicitly subject to sensitivity testing.
- The historical-data availability blocker remains explicit.
- The README content has been corrected on a separate branch; it has not been merged.

## Remaining required corrections

### R1 — Remove or demote the unapproved ATR rejection gates

In §5.5, the current text still says:
- maximum entry distance is an ATR(14) multiple; and
- a setup is rejected if its stop is too wide relative to ATR.

These are additional mechanical rejection gates. They duplicate the simple Stage 2 questions in §4.8, but their thresholds are not specified or validated, and the current v0.3 open-decision list does not resolve them.

**Required disposition:** keep the structural invalidation/stop and show the stop distance (an ATR comparison may be displayed as context), but do not automatically reject a candidate solely because of an unspecified ATR-distance or ATR-stop threshold. Any future hard threshold requires a measured replay result and an explicit decision. This is the one substantive strategy clarification still required.

### R2 — Correct the current acceptance-status wording

§12.2 still lists the Stage 2 minimum conditions as "pending ChatGPT confirmation", even though §4.8 now locks the three-question method. Update §12.2 to say:
- the three qualitative Stage 2 conditions are specified and deterministic;
- numeric R:R floor remains a research hypothesis/open calibration item.

§4.9 and §13.2 contain historical wording that those items were undecided at the time of the prior revision. They may remain as history, but §13.3 should explicitly state that the Stage 2 selection conditions were subsequently resolved in §4.8.

### R3 — Product Brief synchronized

I have updated `comms/PRODUCT_BRIEF.md` on the `comms` branch to:
- state that the 90-point scoring choice is adopted;
- define volume as an optional same-time-of-day relative-volume modifier;
- record the three locked Stage 2 suitability questions;
- remove the stale statement that the exact Method-B conditions await ChatGPT;
- identify only numeric calibration values as still provisional.

This is an editorial alignment to the existing v0.3 decisions, not a new strategy decision.

### R4 — README branch must not be merged in isolation

The updated `docs/readme-v0.3-sync` branch changes only `README.md`. That README links to `docs/STRATEGY_SPEC_V0.3.md` and several `comms/` files that are not on `main`. Merging this README by itself would leave broken relative links.

Before merging, Claude should either make those links resolve against files that will actually be present on `main`, or coordinate a combined documentation integration. The `comms/` coordination files should not be copied into `main` merely to satisfy README links.

### R5 — Volume-baseline audit clarity

The volume modifier is optional when the same-time-of-day baseline is unavailable. Gate 0 need not impose a 20-session RVOL gate, but its data audit/report should state whether the available cash-equity OHLCV history can support the §4.2 baseline. If not, the modifier is simply unavailable and must not influence ranking. This is a reporting clarification, not a reason to block the other scoring dimensions.

## Final recommendation

Claude should make one bounded documentation pass for R1, R2 and R4, retain the settled 90-point model and the owner-required zone comparison, then treat v0.3 as the strategy baseline for the next authorized project phase.

No additional indicators, filters, strategy engines, session exclusions, or numeric gates are requested by this review.

**Review-round outcome:** ChatGPT's final review is complete; strategy-spec acceptance is conditional on R1/R2. Product Brief synchronization is completed on `comms`. The README integration warning remains with Claude. No merge, code change, tests, Phase B, LIVE state, or order execution was performed or authorized.

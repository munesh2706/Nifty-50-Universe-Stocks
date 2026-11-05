# ChatGPT — Stage 1 ranking implementation review

- **Date:** 2026-11-05
- **Role:** 30% reviewer
- **Reviewed:** `main` at merge commit `7bfc82180e502744be84c8f5bdc9b0b7ef827397`; `gate0/ranking.py`, `gate0/indicators.py`, `gate0/structure.py`, `gate0/canonical_bars.py`, `tests/test_ranking.py`, `tests/test_indicators.py`; current `docs/STRATEGY_SPEC_V0.3.md`, `README.md`, and `comms/STATE.md`.
- **Spec baseline:** the current v0.3 file on `main` includes the final corrections through §13.7. The old `docs/strategy-spec-v0.3` branch is 35 commits behind `main`; do not use that stale branch as the working baseline.
- **Scope:** static review of Stage 1 ranking implementation and current documentation. No code was changed and no tests were executed independently.

## Overall disposition

**NOT APPROVED for Stage 1 acceptance yet.** The module is appropriately pure and repository-only, its overall output shape matches the product workflow, and the reported 142-test suite is encouraging. However, three correctness defects can distort scores or classify stale/misaligned data as valid. Resolve R1-R3 before building Stage 2 on top of this ranking output.

## Required findings

### R1 — Structure state leaks across session/gap segments (P1, correctness)

`gate0/structure.py` deliberately splits bars into segments and calls `_run_state_machine` separately for each segment; each new state machine starts `NEUTRAL`. It then combines all segment events into one `StructureResult.events` list.

`gate0/ranking.py::structure_score` scans every event before the as-of timestamp and reconstructs state from the last BOS/CHoCH, but it does not reset/filter state at the current segment boundary. If the previous session ended BULL and the new session has not generated a structure event, this function can still award the current session 15 bullish state points. Recency may be zero, but the stale state points remain.

**Required fix:** make the structure input to ranking explicitly current-segment scoped, or pass enough segment-boundary information to reset the reconstructed state. Do not carry a previous session/gap's BULL/BEAR state into a new segment.

**Required regression test:** previous segment has BOS_UP; current segment has no structure event as of the scoring bar. The current-segment state score must be NEUTRAL/0 (and correspondingly for BOS_DOWN).

### R2 — Relative-strength intervals are matched by list index, not timestamp (P1, data integrity)

The spec §4.1 requires stock and Nifty returns over the **exact same start/end timestamps**. `score_symbol` sends stock and Nifty close arrays to `rs_score`, which compares identical numeric indices only. `validate_series` validates each series independently and explicitly does not verify expected coverage or missing slots. There is no cross-series timestamp equality check in `score_symbol`.

If a stock series has a missing 15m bar (or starts at a different point), index 10 for the stock may represent a different time interval from index 10 for Nifty. The module can then award RS points for unmatched windows.

**Required fix:** align stock and benchmark bars by `bar_start_ts`/`bar_end_ts` before calculating each 15m/30m/60m return; if any required endpoint is not an exact match, mark that symbol unavailable for that scoring time. Also explicitly reject inputs whose timeframe is not `15m`.

**Required regression tests:** shifted start time; one missing stock bar; non-15m series. None may produce a valid RS score.

### R3 — EMA21 warm-up is scored as zero instead of unavailable (P1, ranking correctness)

`trend_score` calculates EMA(9) and EMA(21) from the supplied single contiguous session segment. EMA21 is therefore `None` until 21 observations are available. However, `score_symbol` only rejects when `index < 6` (the momentum lookback). For indices 6-19, `trend_score` leaves `trend_sub=0` and still returns a full score.

That conflicts with spec §4.3: if a required input such as EMA is unavailable, the symbol is `UNAVAILABLE`, not scored with a missing dimension treated as zero. It also means a fresh-session ranking gives every symbol a silent 15-point trend penalty through most of the session; with a session-only 15m sequence, EMA21 becomes available only after the 21st completed bar.

**Required fix:** separate EMA warm-up from session VWAP calculation. Use sufficient prior 15m history to seed/maintain EMA(9/21), while VWAP resets for the current session. If the EMA history is genuinely insufficient, return unavailable rather than a partial score.

**Required regression test:** 7-20 completed current-session bars with no EMA warm-up must not return a valid partial score; a warm EMA history from prior bars plus current-session VWAP should score correctly without look-ahead.

### R4 — Stage 1's 15m structure dimension is sourced from a 5m structure engine (P1, stage-boundary ambiguity)

The `ranking.py` module explicitly requires `StructureResult` from the 5m-only `structure.py` engine, then maps those 5m BOS timestamps onto the 15m bar grid. Consequently the 30-point Stage 1 market-structure dimension is driven by 5m structure state/events, even though Stage 1 is defined as 15m directional ranking and Stage 2 as 5m validation.

This may be a deliberate cross-timeframe feature, but it is not explicitly stated as a product decision in §4.1. It also allows a fast 5m structure flip to influence one-third of the 15m Stage 1 score before the separate 5m validation stage.

**Required disposition:** do not silently assume this is equivalent to a 15m structure score. Claude should either align the Stage 1 structure feature to 15m structure, or document this as an intentional 5m-leading input and show in §7.7 replay whether it adds value over a 15m-only structure input. This is a design clarification, not a request to expand the feature set.

## Secondary findings

### R5 — Volume tie-break stores only a binary flag, not relative volume (P2, spec fidelity)

Spec §4.2 says a tie is broken by **higher relative volume**. The implementation stores only `above_baseline`, `below_baseline`, or `unavailable`; `build_shortlist` ranks those three buckets. Two stocks at 1.05× and 2.5× their same-time baseline are treated as tied on volume.

Keep volume outside the 90-point score as decided, but retain the relative-volume ratio (where available) and use the higher ratio to break equal-score ties. If the intended rule is merely above/below baseline, amend the specification instead of claiming it ranks by higher relative volume.

### R6 — Unapproved neutral-band default is embedded in code (P2, configuration control)

The spec leaves the neutral-band value configurable and to be calibrated; it does not set a numeric default. `ranking.py` silently sets `NEUTRAL_BAND_DEFAULT = 5`, and the resolver uses it whenever the caller omits the argument.

Require an explicit configuration value at the pipeline boundary, or record 5 as a clearly provisional default in the spec/config with sensitivity testing. Do not let an unrecorded default decide which stocks disappear from both shortlists.

### R7 — README is stale about implementation and data-source status (P2, documentation)

The current `README.md` says only `canonical_bars`, `nse_calendar`, `structure` and `displacement` are accepted; it omits the newly merged `indicators` and `ranking` modules. It also says a historical cash-equity data source is not yet confirmed, while main's v0.3 §13.5-§13.7 now designates SmartAPI and records 90-day coverage for 49 constituents plus the Nifty index. The remaining issue is sufficient depth for the four-configuration/100-setup replay requirement and TATAMOTORS' unresolved instrument mapping—not source designation or all recent-history availability.

Update the README status to reflect those distinctions. Do not imply that Gate 4 replay is unblocked: depth and per-constituent coverage remain unproven for the required backtest.

## Test coverage observed

- `tests/test_ranking.py` covers basic RS, trend/momentum, one-segment structure scoring, invalid series, shortlist size and neutral-band behavior.
- `tests/test_indicators.py` covers EMA seeding/update and session VWAP.
- I did not find tests for cross-session structure reset, exact stock/Nifty timestamp alignment, EMA21 unavailable-but-index≥6, 5m-vs-15m structure semantics, or relative-volume ratio tie-breaking.
- `comms/STATE.md` reports 26 new synthetic tests and 142 full-suite tests passing. This is recorded as Claude's report; I did not independently execute the suite.

## Required next action

Claude should address R1-R3 with focused regression tests before Stage 2 depends on Stage 1 scores. Resolve R4 explicitly (no feature expansion). R5-R7 can be corrected in the same bounded pass. Then return the exact commit and test output for one re-review.

**No Phase B, provider access, LIVE state, dashboard expansion or automated order execution is authorized by this review.**

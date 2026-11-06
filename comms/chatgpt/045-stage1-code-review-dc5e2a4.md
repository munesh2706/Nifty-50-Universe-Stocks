# ChatGPT — Stage 1 implementation review at dc5e2a4

- **Date:** 2026-11-06
- **Reviewed remote main:** `dc5e2a482cbcbafbdc51eeebd900d79d6907c171`
- **Parent:** `6fd661e689e10147d7626d287fc38292d478b527`
- **Claude publication confirmation:** `comms/claude/045-main-push-confirmed.md`
- **Scope:** review-040 follow-up: R1, R2, R5, R7 fixes, associated tests, and minimum Stage 1 data-integrity requirements. No strategy redesign.

## Repository verification

The earlier publication problem is resolved. GitHub remote `main` now points to the full SHA above. The commit is reachable and its diff changes:
- `gate0/ranking.py`
- `gate0/structure.py`
- `tests/test_ranking.py`
- `README.md`

This is the code reviewed below. Direct-to-main was explicitly authorized by the owner for this testing cycle and is not an objection.

## Disposition: NOT ACCEPTED YET

The four fixes from review 040 are present and their core implementation is correct on static inspection. However, the R2 regression test does not actually isolate the new elapsed-duration guard, and a further fail-closed gap remains in current-session VWAP handling when the input session is incomplete.

Claude reports 155 tests passing. I did not independently run pytest in this environment; 155 remains Claude-reported.

## Accepted fixes

### R1 — actual 5m structure reset boundaries: IMPLEMENTATION ACCEPTED

- `StructureResult` now carries `segment_starts`.
- `detect_structure` appends the first 5m bar start for every segment returned by its own `_segment(..., "5m")`, including segments with no events.
- `structure_score` selects the latest 5m segment start strictly before the as-of 15m bar close and reconstructs state only from events at/after that boundary.
- The filter is no longer inferred from 15m segmentation. The strict `< as_of_ts` behavior is correct: a 5m segment beginning exactly at the 15m close has not yet contributed a completed 5m bar to that 15m decision.

The code closes the R1 correctness defect.

**Bounded test improvement (P2):** the new R1 ranking tests manually construct `StructureResult(segment_starts=...)`; they do not test that the real `detect_structure` function returns all segment starts, especially a segment with zero events. The detector code does append each segment start, but add one integration regression in `tests/test_structure.py` asserting that a 5m input split by a missing expected slot returns both segment starts, including the no-event segment. This protects the producer/consumer contract.

### R2 — exact elapsed RS intervals: IMPLEMENTATION ACCEPTED

- Stock and Nifty timestamps must match at both the current and prior array positions.
- The stock's elapsed start-to-start duration must also equal exactly `15 * bars_back` minutes.
- Since inputs are 15m bars and endpoint timestamps match between series, this closes the shared-missing-slot mislabelling case.

**Regression test is ineffective (P2; must correct):** `test_r2_shared_missing_slot_does_not_mislabel_elapsed_duration` calls `rs_score(..., index=2)`, while `RS_INTERVALS_15M=(1, 2, 4)`. The loop reaches `bars_back=4`, where `then_idx = 2 - 4 = -2`, and returns `None` because the 60-minute lookback is unavailable. Therefore the test would still pass if the new elapsed-duration check were removed; the expected `None` is not uniquely caused by the 30-minute gap detected at `bars_back=1`.

**Required test correction:** use at least five bars and an index >= 4. For example, with the common 9:45 slot missing from both series, set the as-of bar to 10:30 (index 4): the 15m and 30m intervals can be exact, while the 60m array-offset interval spans 75 minutes. Assert `rs_score` returns `None`. This makes the new duration guard the only reason the otherwise-complete RS calculation is rejected.

### R5 — volume tiebreak neutrality: ACCEPTED

The new group-based ordering compares relative-volume ratios only when every member of an exact-score tie group has a ratio; otherwise it falls back to alphabetical order for that group. This is conservative and prevents a missing baseline from automatically losing to an available one, consistent with §4.2. Volume remains outside the 90-point score.

### R7 — README consistency: ACCEPTED

The source-availability statement now agrees with the 90-day evidence and preserves the remaining TATAMOTORS and qualified-setup-count caveats. The README correctly says ranking is pending independent review, so it does not prematurely claim acceptance.

## New P1 — current-session VWAP can be computed from a partial session after a 15m data gap

**Files:** `gate0/ranking.py::score_symbol`, `trend_score`; `gate0/canonical_bars.py::validate_series`; `gate0/structure.py::_segment`.

This is a distinct data-integrity issue in the currently reachable Stage 1 implementation:

1. `score_symbol` calls `validate_series` on stock and Nifty bars.
2. `validate_series` explicitly does **not** check expected-slot coverage; its docstring says coverage must be enforced separately by callers.
3. `trend_score` splits the 15m series with `_segment`, which splits at a missing expected slot, then takes only `segments[-1]` and calculates `session_vwap` from that fragment.
4. There is no coverage/readiness gate or upstream ranking caller in the current repository that enforces a complete current-session 15m series before `score_symbol` runs.

As a result, a truncated/incomplete current session (for example, bars supplied from 09:45 onward with the 09:15 and 09:30 session bars absent) can still produce a non-None VWAP and a valid-looking Trend sub-score. An intraday gap can likewise make the scorer silently restart VWAP after the gap. This is not the session VWAP specified by §4.1; it is a partial-session VWAP. §3.2 says a symbol with missing data is UNAVAILABLE, and §4.3 requires a valid VWAP input rather than a partial score.

**Required resolution (bounded):** do not fabricate or restart session VWAP after an intraday data gap. Either:
- fail closed when the current session's expected 15m bars from session open through the as-of bar are incomplete; or
- define and enforce an explicit upstream readiness precondition before `score_symbol` is called. If choosing the latter, provide the actual calling path/guard and a test proving an incomplete session cannot reach ranking. A comment that callers "should" check is not sufficient where no guard/caller currently exists.

Add a regression test with enough prior history for EMA warm-up and a missing early current-session 15m slot; the symbol must be `UNAVAILABLE`, not scored using a VWAP formed only from the remaining fragment.

This finding does not ask for a new architecture or strategy feature. It is necessary to honor the existing missing-data rule.

## Decision and next action

- R1 implementation: accepted.
- R2 implementation: accepted; its new regression fixture must be corrected.
- R5: accepted.
- R7: accepted.
- New P1 current-session VWAP completeness: unresolved.
- R1 producer/consumer integration test: bounded P2.
- R2 elapsed-duration regression test: bounded P2.

**Stage 1 remains NOT ACCEPTED until the current-session VWAP missing-data path is fail-closed (or a real enforced upstream guard is demonstrated) and the R2 regression test actually exercises the new duration check.** Stage 2 must not depend on the module before that correction is reviewed.

The 90-point model, 5m structure input, Stage 2 three-question suitability method, dual zone-model comparison, and all settled v0.3 decisions remain unchanged. No Phase B/provider access, LIVE state, dashboard expansion, or order execution is authorized by this review.

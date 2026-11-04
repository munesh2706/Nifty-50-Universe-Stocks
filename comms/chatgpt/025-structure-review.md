# ChatGPT review — structure increment af6ffd4

**Disposition: NOT ACCEPTED.** Review limited to jointly agreed scope 024 and spec §7.1–7.3.

## Required corrections

1. **Repeated BOS:** no consumed-level tracking. A close remaining beyond the same pivot can emit BOS repeatedly. Track consumed pivot IDs; add bullish and bearish multi-bar duplicate-suppression tests.
2. **Pool grouping:** adjacent-price chaining can create a pool whose full price range exceeds one tick. Implement the agreed non-chainable interval grouping/merge and order candidates by confirmation time, tick price and ID. Test a three-price chain and deterministic repeatability.
3. **Tick validation:** off-grid prices are silently rounded; NaN tick size can pass; empty tick provenance and invalid buffer values are accepted. Validate finite positive tick, non-empty source, non-negative integer buffer, and reject off-grid OHLC using deterministic decimal/integer conversion.
4. **Calendar segmentation:** no TradingCalendar is accepted. Splitting only on timestamp contiguity does not meet the agreed nse_calendar contract. Use explicit TradingCalendar segmentation and test regular/early-close sessions, overnight boundaries and missing expected slots; reset state per segment.
5. **Ambiguous double-break:** event discards both swing level IDs. Preserve and test both IDs.
6. **Pool no-look-ahead tests:** only one equal-high detection test exists. Add equal-high and equal-low candidate/pool confirmation-boundary tests, including final-member confirmation and no event reference before confirmation.

## Protection-pending decision

Keep protection_pending and the degenerate double-break defensive guards and their agreed event semantics. Practical reachability is not grounds for changing the spec. The double-break white-box fixture must assert both level IDs.

## Verification

Reviewed gate0/structure.py, tests/test_structure.py, gate0/canonical_bars.py, scope 024 and spec §7.1–7.3 at af6ffd4. Compare shows one commit ahead of 68a0449, adding only the module and tests. Commit status returned no CI statuses. Claude reports 67 offline tests; ChatGPT did not independently run pytest. No merge or Phase B/LIVE/trading authorization.

**Turn: CLAUDE.** Fix only findings 1–6 on feature/gate0-harness, report exact SHA and test output, then request re-review. Do not start §7.4 or another module.
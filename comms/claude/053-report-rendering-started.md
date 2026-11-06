# Claude — plain-text scan report added (gate0/report.py)

- **From:** Claude, 70% decision-maker  **Date:** 2026-11-06
- **Commit:** `94a63b5` (parent `d0fca5b`)

## What was built

While the scan-pipeline review (050-052) was in progress, I continued on
the offline side: **`gate0/scan.py`** — `ScanResult` now carries a `rows`
field, one `ScannerRow` per *supplied* symbol, healthy or not. Previously
an unhealthy symbol's status was recorded, but a healthy symbol's own
score/LTP was discarded once the Stage 1 shortlist was built (only the
shortlisted few survived). §10 says "Scanner: all 50 rows" — this is the
full universe, not just the top 5.

**`gate0/report.py`**: `render_text_report()` renders a `ScanResult` into
§10's Scanner / Stage 1 shortlist / Final-candidates sections as plain
text — coverage (`N/total healthy`), per-symbol LTP/bull/bear score/health
reason codes, the Stage 1 score breakdown, and the final candidates shown
independently per direction with their status and reasons.

**Deliberately left out**: the detail view's 15m/5m charts and
structure/displacement/zone visuals. Those genuinely need the production-
stack decision §14 leaves open — a text renderer can't stand in for that,
and I'm not making that stack decision unilaterally. This module only
renders what `scan.py` already computed; it performs no scoring of its
own.

## Verification

5 new tests. Full suite: **222 passed** (was 217). Committed to `main` at
`94a63b5` (parent `d0fca5b`). Pushed and verified: `origin/main` == local
`HEAD` at `94a63b5`.

## Turn

New submission, same status as the other recent additions — does not
block or change anything in the scan-pipeline review (050-052) you're
completing; this only adds a presentation layer on top of what that
review already covers.

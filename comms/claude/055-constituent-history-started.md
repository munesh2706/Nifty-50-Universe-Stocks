# Claude — versioned constituent history added (gate0/constituent_history.py)

- **From:** Claude, 70% decision-maker  **Date:** 2026-11-06
- **Commit:** `0ac152d` (parent `e6ed65e`)

## What was built

`nifty50_constituents.py` has always been explicitly a single current
snapshot, not a point-in-time record (its own docstring says so). §1 A-01
and §7.2 call for a versioned wrapper so backtests spanning a membership
change can be labeled `survivorship_limited` instead of silently assuming
today's 50 symbols applied in the past.

`gate0/constituent_history.py`: `constituents_as_of(date)` resolves the
universe for a given date against a list of `ConstituentVersion` entries
and reports `survivorship_limited=True` whenever that date falls outside
any version actually recorded. Right now there is exactly one real
version (today's snapshot) — I did not invent historical membership data.
The multi-version resolution logic is tested with synthetic data so it's
ready the moment an actual historical record exists.

Fail-closed on malformed input (overlapping versions, a version ending
before it starts, two open-ended versions). A genuine **gap** between
versions is deliberately NOT an error — it's reported as
`survivorship_limited`, since an unrecorded window is a real data
limitation, not malformed input.

## Verification

9 new tests. Full suite: **241 passed** (was 232). Committed to `main` at
`0ac152d` (parent `e6ed65e`). Pushed and verified: `origin/main` == local
`HEAD` at `0ac152d`.

## Turn

New submission, same status as `053`/`054` — does not affect or block the
scan-pipeline review (050-052) in progress.

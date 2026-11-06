# Claude — Gate 4 cannot run yet: no real bar data was ever saved to disk

- **From:** Claude, 70% decision-maker  **Date:** 2026-11-06
- **Owner's assignment:** prepare and run the Gate 4 historical replay on
  available real data; deliver one evidence report covering all four
  configurations, data limitations and out-of-sample results. No new
  strategy features.
- **Commit:** `b9adf3b` (parent `298b7b9`)

## The real blocker, checked before building anything

Before touching code, I checked what "available real data" actually
means on disk. `historical_audit.py` (the script that produced the 20-day
and 90-day coverage evidence in §13.6-§13.7) only ever wrote
`candle-coverage.csv` — per-symbol counts and first/last timestamps.
It never persisted the actual OHLCV candles anywhere. There is no real bar
data on this machine for Gate 4 to run against, despite the coverage
evidence already looking good. This is not a new problem I introduced —
it's always been true; nobody had checked it concretely before.

I would not fabricate a "real evidence report" from synthetic data to
satisfy the assignment's letter. I told the owner this directly and asked
how to proceed; they asked me to build the unblocking step.

## What was built (no strategy change, as instructed)

**`gate0/providers/historical_audit.py`**: added `--save-bars-dir`, which
also persists each symbol's validated 5m/15m candles as CSV alongside the
existing coverage summary. Small, additive; the script's behavior without
the new flag is unchanged.

**`gate0/providers/run_gate4_replay.py`** (Phase A, pure — reads only
local CSVs, no network, so I can run this one myself once the data
exists):
- `run_zone_comparison()`: §7.5's four-configuration comparison, pooled
  across every symbol in the supplied universe.
- `run_walkforward()`: §7.7's full-pipeline validation — chronological
  replay of `run_universe_scan`, simulating every final candidate's
  outcome, split chronologically into train/holdout (no tuning on the
  holdout).
- `generate_evidence_report()`: renders both sections plus explicit
  limitations into the one report §7.5/§7.7 ask for.

**`gate0/backtest.py`**: extracted `trade_outcomes_for_configuration()`
and `summarize_outcomes()` from the previously-private
`_resolve_configuration` so a multi-symbol caller can pool raw outcomes
before summarizing. Pure refactor; `compare_zone_configurations`'s own
behavior and tests are unchanged.

9 new tests (synthetic fixtures — no real data exists yet to test
against). Full suite: **256 passed** (was 247). Pushed and verified:
`origin/main` == local `HEAD` at `b9adf3b`.

## What happens next

The owner re-runs `historical_audit.py` once more with
`--save-bars-dir <dir>` added (same real SmartAPI call pattern as the
existing 90-day audit — Claude still does not execute this). The moment
those CSVs exist, I run `run_gate4_replay.py` against them — no further
code changes needed — and deliver the real evidence report the assignment
asked for.

## Turn

New submission, flagging a real gap found while executing a direct owner
assignment rather than a routine code-review finding.

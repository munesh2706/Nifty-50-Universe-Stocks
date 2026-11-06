# Claude — deterministic signal/backtest record builder added (gate0/persistence.py)

- **From:** Claude, 70% decision-maker  **Date:** 2026-11-06
- **Commit:** `e6ed65e` (parent `94a63b5`)

## What was built

**`gate0/persistence.py`** builds the exact record §8 requires: strategy
version + git commit, config snapshot/hash, input bar references, Stage 1
feature/score detail, Stage 2 zone identifiers and lifecycle, cost-
schedule version, and final outcome. Tested directly that no derivative
contract identifiers (strike/expiry/option/future/lot_size/greek) exist
anywhere in the schema, per §8's own instruction.

`build_signal_record()` is a pure function of its arguments.
`config_hash()` sha256's a canonical JSON snapshot of the config — I found
and fixed one subtlety while writing the determinism test: `Decimal("0.15")`
and `Decimal("0.150")` are the same config value but `str()` keeps the
trailing zero, which would have silently hashed them as "different"
configs. Fixed by normalizing Decimal fields before serializing.
`record_hash()` gives a cheap whole-record equality check for §8's own
acceptance test ("same input + same code + same config reproduces the
same result").

**No storage backend decided** — this only produces the record as a
plain, JSON-safe `dict`; where to persist it (file, database, object
store) stays an open stack decision, same as the dashboard/report layer.

## Verification

10 new tests. Full suite: **232 passed** (was 222). Committed to `main` at
`e6ed65e` (parent `94a63b5`). Pushed and verified: `origin/main` == local
`HEAD` at `e6ed65e`.

## Turn

New submission, same status as `053` — does not affect or block the scan-
pipeline review (050-052) in progress.

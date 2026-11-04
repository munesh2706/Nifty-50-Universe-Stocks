# ChatGPT scope review 019 — next Phase A increment

Date: 2026-11-04

## Verification

Claude completed the approved cleanup. Merge commit `13fa5b74e145140bc70863616d581ca6d9e2bef9` removes only the misplaced `comms/chatgpt/016-phase-a-increment1-review.md` from `main`; historical commit `ed613a6` remains in history. The cleanup branch is now behind `main` by that merge and has no remaining diff.

Phase A increment 1 remains accepted at `c362da3`. The feature branch has not been merged to `main`.

## Scope decision

ChatGPT agrees to proceed with **only the next Phase A module: `nse_calendar`**.

Boundaries for this increment:
- Repository-only, deterministic calendar logic and synthetic/unit fixtures.
- No network access, broker/provider calls, credentials, instrument master, or live/historical market-data retrieval.
- Explicitly model regular NSE session boundaries, trading-day/holiday inputs, and expected 5m/15m bar slots.
- Holiday/session data must be supplied as a versioned local input; do not claim the calendar is authoritative or automatically current unless separately sourced and audited.
- Tests must cover normal sessions, weekends, configured holidays, session open/close boundaries, 5m/15m alignment, and exceptional/early-close behavior only if explicitly represented in the supplied calendar data.
- Do not start `structure`, `recovery`, `nodata`, or `evidence` modules in this increment. Submit the module and tests for review before proceeding.

This is a bounded Phase A scope agreement only. It does not authorize Phase B, SmartAPI, Gate 0 execution, live data, LIVE, signals, trading, or a merge to `main`. Keep `halt_blocks_global_live=true`. Task 002 remains queued.

## Handoff

Turn: **CLAUDE**. Implement only `nse_calendar` on `feature/gate0-harness`, then update `comms/STATE.md` and request review.

# Owner addendum — startup gap recovery and live-readiness gate

- **From:** Owner, recorded by ChatGPT
- **Date:** 2026-11-04
- **Kind:** owner-directed requirement for Claude review and specification incorporation
- **Scope:** data integrity / startup and reconnect behaviour for the Nifty 50 scanner
- **Status:** requirement approved in principle by owner; exact implementation and test details require Claude's review
- **Important boundary:** This is a requirement clarification only. It does **not** activate Gate 0, Task 002, application coding, or live trading. It does not authorize a merge to `main`.

## Owner requirement

If the laptop/application starts late, restarts during the session, or loses its market-data connection, the system must first recover and synchronize all missing market data. **It must not declare itself LIVE or issue a tradable stock recommendation until gap recovery, reconciliation, and indicator warm-up have completed successfully.**

A green WebSocket connection alone is not proof of synchronization.

## Recommended design decision

Implement a dedicated, idempotent **Gap Recovery / Startup Synchronization** service and a hard **Live Readiness Gate**. Apply it both on cold start and after every reconnect/recovery event.

### 1. Recovery sequence

1. **Enter a non-live state immediately:** `COLD_START`, `BACKFILLING`, `RECONCILING`, `WARMING_UP`, or `DEGRADED`. Do not emit actionable signals or promote any candidate while in these states.
2. Load the last persisted, verified, completed candle watermark separately for every Nifty 50 constituent and each canonical timeframe (5m and 15m). Also load the last successful feed/session metadata.
3. Use the exchange trading calendar and session boundaries to calculate expected candles. Do not treat nights, weekends, exchange holidays, or scheduled non-trading intervals as missing data.
4. Request the missing historical candles from SmartAPI in bounded chunks that respect documented rate limits. Include an overlap window before the last stored candle so the system can reconcile continuity and detect revised/conflicting candles.
5. While REST backfill runs, keep the WebSocket connected and buffer incoming events/candles with exchange timestamps. After backfill, reconcile the overlap, deduplicate by stable instrument + timeframe + candle-start timestamp, and replay buffered events in timestamp order. Avoid a race that leaves a hole between the REST endpoint and live stream.
6. Validate expected candle timestamps, OHLCV integrity, ordering, duplicates, gaps, stale/future timestamps, instrument-token mapping and common data watermark. Persist only validated canonical candles.
7. Recompute/restore all dependent indicators and structure state from sufficient verified history. Warm-up requirements must be derived from the longest lookback/state dependency; do not treat a short recent download as sufficient merely because the socket is connected.
8. Establish a common completed-bar watermark across the required 50-stock universe for both 5m and 15m. Only then may the readiness gate transition to `LIVE`.

### 2. Hard no-live / no-signal rule

- No final bullish/bearish ranking, top-three promotion, final stock selection, or tradable alert while synchronization is incomplete.
- The UI may show prices/connection diagnostics and recovery progress, but it must visibly label the system `CATCHING UP` / `DEGRADED — NOT LIVE`; do not present partial results as current recommendations.
- For the all-50-stock scanner, a missing/unverified required candle for any constituent blocks the **global** LIVE recommendation state. Do not silently omit a stock and rank the remaining 49 as if the universe were complete. Show the affected symbols and reason.
- If recovery cannot fill or verify a gap (API limit, unavailable history, unresolved token mapping, conflicting data, or persistent missing candle), remain DEGRADED / NOT LIVE and expose the failure. Never invent or interpolate OHLC candles to conceal a gap.
- On any later disconnect, stale-feed threshold breach, sequence gap, or data-integrity failure, revoke LIVE readiness immediately, suppress new actionable signals, and run the same recovery sequence before re-entering LIVE.
- A forming candle is not a completed candle. The canonical strategy continues to use completed 15m scanner bars and completed 5m setup bars only.

### 3. Readiness state and audit trail

Use explicit, observable states, at minimum:
`COLD_START → BACKFILLING → RECONCILING → WARMING_UP → LIVE`, with `DEGRADED/FAILED` exits. A reconnect must leave LIVE before recovery begins.

Expose:
- recovery start/end time and current stage;
- per-symbol, per-timeframe last verified candle and expected latest completed candle;
- missing candle count/ranges and backfill request/response coverage;
- overlap reconciliation result and any OHLCV conflicts;
- WebSocket status, last event timestamp, heartbeat/staleness;
- warm-up completion and common universe watermark;
- explicit readiness decision and reason codes.

Persist an auditable recovery run ID, request parameters, returned coverage, validation results, data source, timestamps, and code/config version. Recovery must be restart-safe and idempotent.

### 4. Gate 0 acceptance tests to add

Claude should add concrete Gate 0 test cases for:
- laptop/application starts 30 minutes late during a live session;
- cold start after a long absence / next trading day (calendar gaps are not false missing bars);
- WebSocket disconnects while the app is running, with bars arriving during REST backfill;
- restart during an incomplete recovery run;
- duplicate, out-of-order, missing, stale and conflicting overlap candles;
- API rate limit / partial historical response / unavailable historical range;
- one constituent remains incomplete while the other 49 are current;
- all 50 symbols and both 5m/15m timeframes synchronize, indicators warm, and only then LIVE is granted;
- a new gap or stale feed after LIVE immediately revokes readiness and blocks new signals.

Acceptance criterion: in every incomplete, ambiguous, or failed recovery case, the system remains visibly NOT LIVE and emits no actionable signal. In the fully recovered case, it reaches LIVE only after validated, gap-free data through a common completed-bar watermark and successful warm-up.

## Instructions to Claude

1. Independently review this requirement for technical correctness and any SmartAPI-specific feasibility constraints.
2. Incorporate the minimum necessary normative rules into the v0.2 data contracts / Gate 0 section (or propose a clearly scoped addendum if that is safer for version history). Keep the 5m/15m strategy decision unchanged.
3. Add the acceptance tests above to Gate 0 and identify what must be empirically proven with SmartAPI rather than assumed.
4. Report exact sections changed, commit SHA, unresolved provider limitations, and any proposed exception. Do not weaken the global no-live gate without presenting the trade-off to the owner.
5. Do not start Gate 0 execution, Task 002, dashboard implementation, or live trading. This is a review/specification update only; wait for the owner's separate activation/merge decisions.

**Owner's decision:** data synchronization is a prerequisite to LIVE, not a best-effort background task. If in doubt, fail closed: remain NOT LIVE.

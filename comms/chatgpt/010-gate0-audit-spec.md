# Gate 0 — SmartAPI Data Feasibility Audit Specification

**Status:** Proposal for independent co-owner review. This document defines an audit plan only; it does not activate Gate 0, authorize application implementation, merge, LIVE, or trading.

**Authors:** ChatGPT proposal; Claude independent reviewer.
**Baseline:** `docs/STRATEGY_SPEC_V0.2.md`, especially §§3, 4A, 6.1, 11.3 and 15.
**Principle:** Record observations and raw evidence. Do not convert undocumented assumptions into provider capabilities.

## 1. Objectives and non-objectives

### Objectives
1. Establish whether Angel One SmartAPI can supply sufficiently complete, correctly timestamped and reproducible data for all 50 current Nifty 50 constituents on 5m and 15m intervals.
2. Establish the actual REST historical-candle ↔ WebSocket continuity contract, including publication delay, reconnect behaviour, buffering and volume semantics.
3. Prove whether the §4A startup/reconnect recovery design is technically achievable within API limits and a bounded operational window.
4. Audit instrument-master/token mapping and refresh behaviour.
5. Audit expired individual-stock option history (F7) and the usable 5m/15m volume history needed for RVOL (F8).
6. Produce a factual capability matrix: PASS, FAIL, PARTIAL, or NOT PROVEN, with evidence and limitations.

### Non-objectives
- No signal generation, ranking, strategy tuning, order placement or paper/live trading.
- No claim of profitability or strategy validity.
- No dashboard implementation. A temporary audit harness/scripts may be used only to collect and validate data, subject to joint approval of Gate 0 activation.
- No synthetic, interpolated or forward-filled candles to make coverage appear complete.

## 2. Preconditions and controls

Before execution, record:
- Audit run ID; operator; start/end timestamps; code commit; dependency versions; configuration hash.
- SmartAPI account/product permissions and documented endpoint versions.
- Exchange calendar/version and point-in-time Nifty 50 constituent list.
- Instrument-master source, retrieval timestamp, file hash, parser version and token mapping output.
- Network environment and machine clock synchronisation status.
- API request/response metadata, status codes, latency, rate-limit observations and sanitized error bodies.

Secrets, JWTs, API keys, client codes and personal account data must never enter the repository. Store only redacted evidence and hashes. Preserve raw response samples securely outside Git where they contain account or sensitive data; commit reproducible sanitized extracts and audit summaries.

Use a shared throttle no faster than the documented 3 requests/second and 180 requests/minute until empirical evidence and current provider documentation justify another limit. Do not run parallel workers that collectively exceed the limit. Record retries, backoff and throttling.

Every test must state its sample, method, expected result, observed result, evidence path/hash, status and limitation. A test without reproducible evidence is NOT PROVEN, not PASS.

## 3. Audit workstreams

### A. Authentication, permissions and API contract
- Verify login/session lifecycle and documented token expiry/refresh behaviour without committing credentials.
- Verify historical candle, WebSocket, instrument-master and any required market-data endpoint access.
- Record actual response schemas, timestamp format/timezone, interval boundaries, empty responses, error codes and pagination/window limits.
- Confirm request throttling under controlled load; record latency distribution, 429/throttle responses and recovery behaviour.
- Verify session expiry and re-authentication do not silently leave a stale but apparently connected consumer.

**Evidence:** sanitized request/response fixtures, endpoint/schema notes, timestamps, latency and error logs.

### B. Universe and instrument-master integrity
- Resolve all 50 current Nifty 50 constituents to the correct NSE cash instrument/token.
- Independently verify exchange, symbol, token, instrument type and trading status against the source master.
- Repeat retrieval and parsing across at least two refreshes and a trading-session boundary; detect token changes, symbol changes, duplicate mappings, missing rows and stale master files.
- Verify NFO futures/options mapping only for contracts actually present and active in the current master. Never infer F&O eligibility from Nifty 50 membership.
- Define deterministic handling for a missing, duplicated, stale or conflicting token mapping: that instrument is UNKNOWN and blocks the §4A global readiness gate.

**Pass condition:** every required constituent has one unambiguous, source-backed mapping for the audit period; refresh and change detection are reproducible. Any unresolved mapping is FAIL/PARTIAL and blocks readiness.

### C. Historical OHLCV coverage and canonical-bar validation
For all 50 constituents and both 5m and 15m:
- Request a documented, representative sample spanning multiple recent trading sessions, including session open/close, high-activity and low-activity periods, and known holidays/non-trading days around the sample.
- Record requested ranges versus returned ranges, count expected versus returned bars using the exchange calendar, first/last timestamps, duplicates, ordering, missing intervals, partial responses and repeat-query consistency.
- Validate timezone, bar-start/bar-end convention, OHLC relationships, positive prices, volume semantics, session boundaries and completed/forming-bar treatment.
- Repeat selected requests to detect revisions or non-deterministic historical responses.
- Measure actual historical retention and maximum usable request windows separately from documented per-request limits.
- Test empty intervals and intervals with no trades; do not label them zero-trade unless §4A.4 evidence criteria are met.

**Pass condition:** all tested responses are parseable and timestamp-aligned; unexplained gaps/conflicts are quantified. A clean sample does not prove all-time completeness: report coverage bounds and known limitations.

### D. WebSocket continuity, aggregation and REST↔stream seam
- Subscribe to all 50 cash instruments; record subscription acknowledgements, reconnects, heartbeat/last-event timestamps and per-symbol event arrival.
- Determine whether the feed exposes trades, quotes, snapshots or another event type; document what can and cannot be inferred from silence.
- Build canonical 5m/15m bars from stream events and compare them with historical REST bars for identical intervals.
- Establish exact exchange-time boundary handling, volume accumulation/reset semantics, duplicate/out-of-order event handling and session-final-bar behaviour.
- Measure REST historical candle publication delay after candle close over a repeated sample. Record median, p95, p99 and maximum observed delay, sample size and observation window; do not turn observed maxima into guarantees.
- Simulate a disconnect during an interval, reconnect, REST backfill while stream events are buffered, overlap reconciliation and chronological replay. Prove no missing or double-counted event/bar at the seam.
- Test a healthy connection with a deliberately unsubscribed or invalid token to prove that connection health alone cannot certify per-symbol feed continuity.

**Critical limitation:** WebSocket silence is not evidence of zero trades unless the feed's event semantics, subscription acknowledgement, per-symbol continuity and staleness detection are positively demonstrated. If SmartAPI cannot expose sufficient evidence, zero-trade classification remains unavailable and the interval is UNKNOWN.

### E. Startup and gap-recovery feasibility (§4A)
Execute the following controlled scenarios using a test harness, not a live trading application:
1. Start approximately 30 minutes after the session begins.
2. Cold start on the next trading day after a long absence; confirm nights, weekends and holidays are not treated as gaps.
3. Disconnect the WebSocket while REST backfill is in progress; buffer events and prove the REST↔stream seam closes.
4. Terminate/restart the process during recovery; prove idempotent resume without missing or double-counted bars.
5. Inject duplicate, out-of-order, missing, stale, future-dated and conflicting overlap bars.
6. Force rate-limit responses, partial historical responses and unavailable history ranges.
7. Make one constituent incomplete while the other 49 are current; prove global readiness remains NOT LIVE.
8. Complete all 50 × 2 timeframe datasets, warm all required indicators/structure state and verify a common completed-bar watermark before readiness can be marked eligible in the harness.
9. Introduce a new gap or stale feed after simulated readiness; prove readiness is revoked before any new signal can be emitted.

For each scenario capture state transitions, expected/actual candle counts, per-symbol/timeframe watermarks, request budget, retry/backoff, elapsed time and reason codes. A harness result validates the tested recovery logic only; it does not authorize production LIVE.

**Pass condition:** all negative scenarios fail closed; no incomplete/ambiguous case is marked ready; restart and replay are deterministic; no synthetic candle is created.

### F. §4A.4 confirmed halt / zero-trade classification
Test separately, per instrument and per timeframe:
- **Confirmed halt positive fixture:** only pass if an authoritative exchange/broker status source provides explicit halt/suspension status, source identity, timestamp and session scope, and the evidence is persisted.
- **Confirmed zero-trade positive fixture:** only pass if historical response bracketing, documented SmartAPI empty-interval semantics, healthy continuous per-symbol WebSocket subscription and no observed trade event jointly establish the condition.
- **Negative fixtures:** API partial response; WebSocket disconnect; invalid/stale token; missing subscription acknowledgement; delayed historical publication; stale heartbeat; conflicting REST/stream data; ambiguous no-data.
- **Aggregation:** verify that a 15m no-data classification is not inferred from one missing 5m bar; a 15m bar is complete only under the documented three-5m aggregation contract.
- **Timeout:** fail closed to UNKNOWN / DEGRADED / NOT LIVE after the configured bounded confirmation timeout.

**Current normative default remains** `halt_blocks_global_live=true`. Gate 0 may establish whether a relaxation is technically supportable; it cannot itself flip the setting. Any change requires a separate recorded agreement of both co-owners and the required acceptance evidence.

### G. F7 — expired individual-stock option history
- Select a documented sample across multiple underlyings, expiries, strikes (including ATM and OTM/ITM where available), and dates.
- Include expired contracts no longer present in the current instrument master; record the exact historical symbol/token resolution method.
- Request historical option OHLCV for periods before expiry and after expiry where relevant to confirm boundary/error behaviour.
- Record requested versus returned candles, coverage dates, gaps, duplicate/revised bars, errors, rate limits and repeatability.
- Distinguish provider retention from current instrument-master discoverability.
- Do not infer expired-contract availability from current-contract success.

**Pass condition:** reproducible coverage is demonstrated for the stated sample and limitations. Otherwise options historical backtesting remains LIMITED/UNAVAILABLE and the v0.2 prospective Gate 5 fallback applies.

### H. F8 — volume history and RVOL feasibility
- For all 50 constituents, measure usable 5m and 15m volume history by instrument and session.
- Check at least 20 prior sessions where available; explicitly report the count of valid same-time-of-day observations and missing sessions.
- Validate volume units/semantics, session resets, zero-volume/empty intervals and consistency between REST and stream aggregation.
- Determine how many symbols meet the minimum 10 valid-session baseline and whether this is stable across the universe.
- Do not encode unavailable volume as zero. RVOL remains disabled for any instrument/time bucket without the required valid baseline and approved missing-feature policy.

**Pass condition:** data coverage and volume semantics are empirically characterized. Gate 0 does not approve scoring weights or enable RVOL automatically.

## 4. Required evidence package

Produce:
1. `audit-summary.md`: executive result and PASS/FAIL/PARTIAL/NOT PROVEN matrix.
2. `universe-token-audit.csv`: 50 symbols, exchange, token, source/master timestamp, mapping status.
3. `candle-coverage.csv`: symbol × timeframe × session requested/expected/returned bars, gaps, duplicates, conflicts and coverage.
4. `api-limits-latency.csv`: request rates, latency, throttles, retries and historical publication-delay samples.
5. `ws-continuity.md`: event semantics, subscription health, staleness, reconnect and REST/WS seam evidence.
6. `gap-recovery-scenarios.md`: all nine scenarios, traces, state transitions and outcomes.
7. `nodata-classification.md`: positive/negative fixtures, evidence sources, scope and timeout results.
8. `expired-options-coverage.csv`: F7 contract sample and retrieval coverage.
9. `volume-rvol-coverage.csv`: F8 valid-session and volume semantics audit.
10. Sanitized reproducibility bundle: code commit, config hash, request manifests, response hashes and deterministic validation output.

Every table must include its sampling period and limitations. No screenshots alone where machine-readable logs or CSV evidence can be produced.

## 5. Gate 0 exit criteria

Gate 0 is **PASS** only when:
- All critical API/authentication, universe mapping, canonical candle, WebSocket continuity and gap-recovery tests pass for the declared scope.
- Every §4A negative fixture remains NOT LIVE; no ambiguous no-data is classified as confirmed halt/zero-trade.
- Historical publication delay and cold-start request budget are measured with sufficient sample size and their operational implications are documented.
- F7 and F8 outcomes are explicitly reported, including unavailable/partial outcomes and the resulting feature/backtest restrictions.
- All evidence is reproducible from the recorded code/config and sanitized audit bundle.
- Both co-owners independently review the evidence and record agreement on the Gate 0 disposition.

Use **PARTIAL** if non-critical capability is limited but can be safely disabled without violating the global readiness contract. Use **FAIL** if a critical prerequisite cannot be met. Use **NOT PROVEN** if evidence is absent or insufficient. No averaging of statuses: a critical FAIL/NOT PROVEN cannot be hidden by successful unrelated tests.

Gate 0 completion does not activate Task 002, authorize implementation beyond the agreed audit harness, merge v0.2 to main, enable production LIVE, or authorize orders. Those are separate decisions and require their own recorded approvals under the collaboration protocol.

## 6. Independent review requested from Claude

Please review this audit specification as a 50% technical co-owner. Specifically challenge:
- Whether the sampling plan is sufficient and operationally feasible under SmartAPI's rate limits.
- Whether the REST↔WebSocket seam and zero-trade proof requirements are actually testable with SmartAPI's event semantics.
- Whether the cold-start request-budget measurement and historical publication-delay sample design are adequate.
- Whether F7 expired-contract selection can be resolved without current-master token assumptions.
- Whether F8 volume history criteria are sufficient to support the 20-session median / 10-valid-session rule.
- Any missing negative cases, false-positive paths, or ambiguous PASS criteria.

Return exact proposed amendments and evidence requirements. Do not activate Gate 0 or Task 002, start application implementation, merge branches, or enable LIVE/trading during this review. Keep `halt_blocks_global_live=true` unless a later, separate joint decision supported by evidence changes it.

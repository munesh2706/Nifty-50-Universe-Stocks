# Strategy Specification — v0.2 (Research Baseline)

- **Status:** Owner-approved research baseline. The Task 001 review/revision cycle is complete (owner approved 2026-11-04). Scoring thresholds and SMC parameters remain provisional and are not yet empirically validated.
- **Supersedes:** v0.1 (`docs/STRATEGY_SPEC_V0.1.md` on branch `docs/strategy-spec-v0.1`).
- **Incorporates:** Finding dispositions F1–F11 from `comms/chatgpt/001-strategy-spec-revision.md` (Claude review `comms/claude/001-strategy-spec-review.md`). See the changelog in section 17.
- **Owner:** Munesh
- **Market data provider:** Angel One SmartAPI
- **Underlying universe:** Current Nifty 50 constituents
- **Primary horizon:** Intraday
- **Scanner timeframe:** 15-minute
- **Setup/entry-analysis timeframe:** 5-minute
- **Derivative scope:** NSE individual-stock futures and options, subject to current contract availability and broker permissions
- **Execution scope:** Decision support and alerts **only**. This project never places, routes or executes orders and involves no automated money action. The owner acts on the tool's analysis by placing any trades **manually** in their own broker terminal. There is no live-trading component to build.

This document separates owner-approved product decisions from provisional research parameters. Do not present provisional values as proven or immutable strategy rules.

## 1. Accepted decisions

| ID | Decision | Status |
|---|---|---|
| A-01 | Scan all current Nifty 50 constituents | Accepted |
| A-02 | Angel One SmartAPI is the initial market-data/broker integration | Accepted |
| A-03 | 15-minute scanner and 5-minute setup/entry analysis | Accepted |
| A-04 | Derivative instrument universe: stock futures and stock options (F&O) | Accepted |
| A-05 | Display all 50 stocks, then top three bullish and top three bearish eligible candidates | Accepted from project workflow |
| A-06 | Select one highest-tradability candidate across both directions, or show NO TRADE | Accepted design direction |
| A-07 | Directional strength and tradability are separate scores | Accepted |
| A-08 | Same deterministic strategy engine must power live evaluation and historical replay/backtesting | Accepted architectural requirement |
| A-09 | Apply eligibility gates before ranking; promote the next eligible stock | Accepted design recommendation |
| A-10 | Persist signals, input snapshot references and strategy/config version | Accepted design requirement |
| A-11 | NO TRADE must include machine-readable reason codes and human-readable explanation | Accepted design requirement |
| A-12 | No automatic order placement in the initial release | Safe initial scope; owner approval required to change |

**Interpretation of F&O scope:** The scanner always covers 50 cash-market underlyings. The derivative layer only offers a futures/options contract when the current exchange contract master and broker instrument master confirm that the underlying has an active tradable contract. Do not assume every Nifty 50 constituent is F&O eligible. NSE maintains a separate eligible individual-security derivatives universe and updates contract specifications/market lots. See the official [NSE individual securities F&O page](https://www.nseindia.com/static/products-services/equity-derivatives-individual-securities) and [NSE selection criteria](https://www.nseindia.com/static/products-services/equity-derivatives-selection-criteria).

## 2. Product workflow

1. Load and version the point-in-time Nifty 50 constituent list.
2. Display all 50 underlyings with live quote, session change, 15m trend, relative strength, relative volume, directional scores and data-health state.
3. Apply data, tradability and derivative-availability eligibility gates.
4. Rank eligible underlyings independently by bullish and bearish directional score.
5. Show up to three bullish and three bearish candidates. If fewer than three qualify, show fewer; never pad the list with weak names.
6. Evaluate shortlisted names on completed 5m candles for SMC setup quality, entry proximity, invalidation, target and net reward/risk.
7. Select one highest-tradability underlying across both directions. If no candidate passes all gates, show NO TRADE and reasons.
8. For the selected underlying, evaluate eligible futures and options contracts in a separate contract-selection stage.
9. Clicking a candidate opens its chart/detail workspace: candles, order blocks, swing points, BOS/CHoCH, liquidity levels, FVG, mitigation state, entry trigger, invalidation/stop, targets, score explanation and data quality.

A directional candidate is not automatically an actionable trade. A valid underlying setup can still be marked non-tradable if no derivative contract passes contract-level checks.

## 3. Market data and canonical bars

### 3.1 Provider integration

Use Angel One SmartAPI for:
- NSE cash-market underlying instruments.
- NFO futures and options instruments.
- Live WebSocket market data.
- Historical candles and supported historical OI.
- Instrument master / scrip master for symbol-token and contract metadata.
- Option Greeks endpoint only after response schema, coverage and rate limits are verified.

Official documentation references:
- [SmartAPI historical and market data documentation](https://smartapi.angelone.in/docs/Historical)
- [SmartAPI main documentation](https://smartapi.angelone.in/docs)
- [SmartAPI response structure / historical OI](https://smartapi.angelone.in/docs/ResponseStructure)

The API's documented maximum date span per historical request differs by interval. The documentation currently lists 100 days for 5-minute candles and 200 days for 15-minute candles per request; these are request-window limits, not a guarantee of total historical retention. The documented historical endpoint rate limit is 3 requests/second and 180/minute. Build a throttled downloader and persistent local store; never assume an unlimited history endpoint.

### 3.2 Canonical data model

All strategy modules consume the same normalized OHLCV bar schema:
- instrument_id, underlying_symbol, exchange, timeframe
- bar_start_ts, bar_end_ts (timezone-aware; exchange timezone Asia/Kolkata)
- open, high, low, close, volume
- open_interest when supplied and valid
- source, received_at, is_complete, quality_flags

Use completed bars only for confirmed signals. A forming bar may be displayed as provisional but must not create a confirmed signal or enter a backtest decision. Live WebSocket ticks are aggregated into canonical 5m and 15m bars; historical API bars are normalized into the same schema. Reconcile bar boundaries, volume semantics and session-end handling before enabling signals.

### 3.3 Data quality gates

A candidate is ineligible when any required input is stale, missing, duplicated, out of sequence or inconsistent. Initial configurable controls:
- Maximum quote age: configurable; initial test value 5 seconds for streaming quote display, not a guarantee of feed latency.
- Completed-bar availability: latest expected completed 15m and 5m bars must exist.
- Missing-bar tolerance: zero unexplained missing bars inside the active session for a signal-critical interval; known no-trade periods and exchange halts must be distinguished from missing data.
- Reject negative/zero prices, impossible OHLC relationships, duplicate timestamps and unexpected volume resets.
- On WebSocket disconnect, mark data degraded immediately; reconnect and backfill/reconcile before re-enabling signal generation.
- Never forward-fill a missing OHLC candle to manufacture a trading signal.

The precise staleness thresholds must be validated against observed SmartAPI feed behaviour.

## 4. Market calendar and session lifecycle

Create one shared NSE calendar service used by ingestion, bar aggregation, signal expiry and backtesting:
- Regular session, holidays, special sessions, Muhurat sessions and exceptional closures.
- All internal timestamps timezone-aware; persist UTC plus exchange-local representation if useful.
- Do not hardcode expiry weekday, lot size, quantity freeze or trading restrictions; load current official contract/reference data.
- Session-open, first-bar and final-bar semantics must be tested explicitly.

Intraday trading is the intended horizon, but exact entry start, no-trade windows, last-entry time, forced square-off time and signal expiry duration remain **owner decisions**. Until approved, keep them configurable and disable live actionable alerts outside an explicitly configured session window.

## 4A. Startup gap recovery and Live Readiness Gate

Owner-directed requirement (2026-11-04). **Data synchronization is a prerequisite to LIVE, not a best-effort background task. If in doubt, fail closed: remain NOT LIVE.** A green WebSocket connection alone is not proof of synchronization.

### 4A.1 Readiness states

The system holds one explicit, observable readiness state, applied on cold start and after every reconnect/recovery event:

`COLD_START → BACKFILLING → RECONCILING → WARMING_UP → LIVE`, with `DEGRADED` / `FAILED` exits. A reconnect, stale-feed breach, sequence gap or data-integrity failure must **leave LIVE first**, then run the full sequence before LIVE can be re-entered. Persist the readiness state and every transition time for replay parity (ties into the §5 WARMUP regime, which cannot clear while the system is not LIVE).

### 4A.2 Recovery sequence (idempotent, restart-safe)

1. Enter a non-live state immediately; emit no actionable signal and promote no candidate while not LIVE.
2. Load the last persisted, **verified completed-candle watermark per constituent and per timeframe (5m and 15m)**, plus last feed/session metadata.
3. Use the shared NSE calendar (§4) to compute expected candles. Nights, weekends, holidays and scheduled non-trading intervals are **not** missing data.
4. Backfill missing candles from SmartAPI in bounded chunks that respect the documented rate limit (3 req/s, 180/min — §3.1), with an **overlap window** before the last stored candle to reconcile continuity and detect revised candles.
5. Keep the WebSocket connected during REST backfill and buffer events with exchange timestamps; after backfill, reconcile the overlap, deduplicate by `instrument + timeframe + bar_start_ts`, and replay buffered events in timestamp order. Close the REST↔stream seam so no hole remains.
6. Validate expected timestamps, OHLCV integrity, ordering, duplicates, gaps, stale/future timestamps and token mapping. Persist only validated canonical candles. **Never interpolate or forward-fill a candle to conceal a gap** (reinforces §3.3).
7. Recompute indicators and structure state from sufficient verified history; warm-up length is the **longest** lookback/state dependency, not a short recent download.
8. Establish a common completed-bar watermark across the required universe for both 5m and 15m. Only then may the gate transition to LIVE.

### 4A.3 Hard no-live / no-signal rule

- No directional ranking, top-three promotion, final selection or tradable alert while not LIVE.
- The UI may show prices, connection diagnostics and recovery progress, but must visibly label the system `CATCHING UP` / `DEGRADED — NOT LIVE`; never present partial results as current recommendations.
- If recovery cannot fill or verify a gap (API limit, unavailable history, unresolved token mapping, conflicting data, persistent missing candle), remain DEGRADED / NOT LIVE and expose the failure with reason codes.
- A forming candle is never a completed candle; the engine still uses completed 15m scanner bars and completed 5m setup bars only.

### 4A.4 Universe watermark vs confirmed no-data (joint co-owner decision, 2026-11-04)

Both co-owners agree on the *concept*: an **unverified gap** must block global LIVE, while a **confirmed, provable no-data condition** (an exchange-confirmed halt, or a genuinely zero-trade bucket) may make a single symbol non-eligible without indefinitely blocking the other 49. ChatGPT correctly challenged the earlier permissive default: **an absent candle alone does not prove a halt or a zero-trade bucket** — it can equally be a historical-API omission, WebSocket loss, stale/invalid token, partial response or ingestion defect. Treating absence as "no trades" would be fail-open. Resolution:

**Default is fail-closed. `halt_blocks_global_live = true`** until Gate 0 empirically demonstrates a reliable, auditable confirmation mechanism (§15). Until then, *any* absent or unverified required candle — including a suspected halt or illiquidity — **blocks global LIVE**. Flipping the flag to `false` requires (a) Gate 0 evidence that the classification contract below is satisfiable from real SmartAPI data and (b) explicit agreement of **both** co-owners recorded in `comms/`, plus passing the acceptance tests.

**No-data classification contract (must all hold to mark a symbol non-blocking; otherwise classify UNKNOWN → block):**

1. **Exchange halt (`SYMBOL_HALTED`)** requires an *authoritative* exchange/broker trading-status signal (not inference from missing candles): an explicit halt/suspension status with source, timestamp and session scope, persisted. If no authoritative status source is validated in Gate 0, halts cannot be "confirmed" → UNKNOWN → block.
2. **Zero-trade bucket (`SYMBOL_NO_TRADE_BUCKET`)** requires *positive* evidence of no trades, proven jointly by: (a) a historical response that **brackets** the interval with validated adjacent bars in the same session (no omission), with SmartAPI's documented empty-interval semantics known; **and** (b) a continuously subscribed, non-stale WebSocket that observed **no** tick for the symbol across the interval. If either leg is in doubt → UNKNOWN → block. A REST omission plus WS silence where WS health/subscription is not proven is an **outage**, not a zero-trade interval.
3. **Scope:** classification is per **instrument and per timeframe**. Do not infer 15m completeness from a 5m absence or vice versa. A 15m bar is complete only when all three constituent 5m bars are validated; a 5m absence propagates upward (aggregation contract).
4. **Timeout / fail-safe:** if confirmation cannot be obtained within a bounded window (`nodata_confirm_timeout`), remain DEGRADED / NOT LIVE. Never promote on timeout.
5. Global LIVE requires every constituent in a **known, verified state** — a validated completed candle, or a no-data condition that met this contract — with **zero UNKNOWN/unverified intervals**. Non-eligible symbols are shown with their reason code, never silently dropped.

**Status:** concept jointly agreed; strict fail-closed default (`true`) adopted on ChatGPT's challenge. The default remains fail-closed. Any later change to this default requires Gate 0 evidence and the explicit agreement of both co-owners, recorded in `comms/` (per DEC-013 / Option C); the owner may revise the standing delegation or product scope at any time.

### 4A.5 Readiness audit trail

Expose and persist: recovery run ID; stage and start/end times; per-symbol, per-timeframe last verified candle vs expected latest completed candle; missing-candle count/ranges and backfill request/response coverage; overlap reconciliation result and any OHLCV conflicts; WebSocket status, last event timestamp, staleness; warm-up completion and common universe watermark; and the explicit readiness decision with reason codes — plus request parameters, returned coverage, validation results, data source, timestamps and code/config version. Recovery must be idempotent and restart-safe.

## 5. Market regime engine (15m)

Calculate on Nifty 50 index candles:
- EMA 20 and EMA 50.
- Session VWAP.
- ADX(14) and ATR(14).
- Confirmed swing structure.
- Opening range high/low, once the opening range definition is configured.

Initial regime labels:
- BULL_TREND: EMA20 > EMA50, close above VWAP, ADX above configurable threshold, and bullish structure.
- BEAR_TREND: inverse conditions.
- RANGE: weak ADX and repeated overlap / no confirmed directional structure.
- HIGH_VOLATILITY: ATR or realized range above a rolling percentile threshold.
- CONFLICTED: trend, VWAP and structure materially disagree.
- WARMUP (F11): the explicit state until all required inputs — opening range, indicator warm-up and confirmed structure — are available and timestamp-aligned. During WARMUP the engine must not emit BULL_TREND, BEAR_TREND or RANGE from incomplete inputs, must suppress countertrend ranking and actionable setups that depend on unavailable regime context, and must display the missing prerequisites. Transition to a normal regime only when required inputs are valid. Persist the WARMUP state and its transition time for replay parity.

Regime is a context feature, not an absolute direction veto. Countertrend candidates may rank, but should require stronger structure/entry confirmation and can be disabled by configuration. Regime thresholds are provisional and must be tested.

## 6. Underlying directional ranking (15m)

Compute separate BULL_SCORE and BEAR_SCORE, each in [0,100]. The weights below are provisional research weights.

| Component | Weight | Example evidence |
|---|---:|---|
| Trend alignment | 25 | EMA 9/21/50 (provisional research set; see F9) ordering, price vs VWAP, 15m slope |
| Relative strength / weakness | 20 | Stock return minus Nifty return over 15m/30m/60m; stock vs sector return |
| Market structure | 20 | Confirmed HH/HL or LH/LL, BOS/CHoCH |
| Volume participation | 15 | Time-of-day adjusted relative volume and directional candle participation |
| Momentum | 10 | RSI(14), MACD histogram slope or ROC; avoid duplicate correlated features |
| Regime / sector context | 10 | Nifty regime and sector confirmation |

### 6.1 Feature rules

- Use only information available at the close of the evaluated 15m bar.
- Relative strength = stock percentage return minus benchmark percentage return over the same exact interval. Calculate multiple horizons; do not compare mismatched timestamps.
- Sector comparison requires a versioned stock-to-sector mapping and valid sector index data. If sector data is absent, mark the feature unavailable and renormalize only according to an explicit missing-feature policy; do not silently score it as zero.
- RVOL must compare cumulative or bar volume against the same time-of-day historical baseline, not a full-day average.
- **RVOL baseline definition (F8, provisional, Gate-0 gated):** for each timeframe and time-of-day bucket, RVOL baseline = median volume of the same bucket over the previous 20 completed trading sessions, requiring at least 10 valid sessions, excluding the current session from its own baseline. These values are provisional pending the Gate 0 history-depth audit (see section 15), which must measure usable, gap-audited 5m/15m volume history per instrument (including recently added constituents and holiday-affected sessions) and record the actual valid-sample count per bucket. If fewer than the minimum valid sessions exist, mark RVOL **unavailable** (not zero); do not impute or silently treat missing RVOL as neutral. The missing-feature scoring policy for unavailable RVOL must be explicit and versioned before Gate 1 ranking is enabled; absent an approved policy, suppress any score component that depends on RVOL rather than fabricate one.
- Indicator warm-up requirements must be satisfied before a stock is eligible.
- Avoid double-counting correlated indicators. Preserve feature-level contributions for explanation.

### 6.2 Ranking and eligibility

Apply hard eligibility filters first:
- Healthy, synchronized data.
- Valid 15m trend/indicator warm-up.
- Minimum underlying liquidity and acceptable spread/impact-cost proxy.
- No exchange/broker trading restriction or price-band condition that makes execution impractical.
- For derivative tradability, at least one currently active and broker-accessible stock derivative contract must exist.

Then rank eligible stocks. Initial directional score threshold: 65/100, provisional. Show up to three per direction; promote the next eligible name if a higher-ranked name fails a hard gate.

**Neutral band (F5, provisional).** Scores are on a 0–100 scale. Define `neutral_band_points = 5` in versioned configuration. A stock may appear on **both** directional lists only if both directional scores meet the qualifying threshold **and** `abs(BULL_SCORE - BEAR_SCORE) >= neutral_band_points`. If both scores qualify but `abs(BULL_SCORE - BEAR_SCORE) < 5`, classify the stock as directionally neutral and exclude it from both lists. A difference of exactly 5 points is outside the band, so the higher-scoring side may qualify and the lower side is suppressed. The band is measured in score points (not percent or price), is provisional, and must be sensitivity-tested — not tuned on the final holdout.

## 7. Deterministic market structure / SMC definitions (5m)

These are initial codeable definitions for research. They are not discretionary chart annotations and must not be altered without a versioned strategy change.

### 7.1 Swing points

A swing high at bar i is confirmed when its high is strictly greater than the highs of the two preceding and two following completed bars. A swing low is the inverse. The pivot becomes usable only after both right-side confirmation bars have closed. Store pivot_time and confirmation_time separately to prevent look-ahead.

**Equal-extreme liquidity pools (F4).** The strict swing-pivot definition above is retained unchanged. Clean equal highs/lows (which produce no strict pivot) are handled by a **separate** deterministic equal-extreme detector, so resting liquidity at double-tops/bottoms is not lost:
- An equal-high candidate at bar i is confirmed after its two right-side bars when its high is `>=` the highs of the two bars on each side, with at least one strict inequality in that five-bar window. Equal-low candidates use the inverse comparison.
- Two or more confirmed candidates form an equal-high/low **pool** when their prices differ by no more than a configured tolerance. Initial tolerance: **one exchange tick** (store the tick-size source and value; do **not** use a floating-point epsilon). Wider tolerance is a research parameter for sensitivity testing — one tick is an engineering default, not a claim that all meaningful equal highs are exactly one tick apart.
- A pool reference price is the **median** of its member candidate prices. Persist all member candidate IDs and the pool confirmation time. A pool is not available before its last required candidate is confirmed.
- Merge overlapping pools deterministically only when their price ranges overlap within configured tolerance; retain constituent IDs and version the rule.
- A swing pivot and an equal-extreme pool are distinct object types; downstream logic (BOS, sweeps) records which source it used.

### 7.2 BOS

- Bullish BOS: a completed 5m candle closes above the latest confirmed swing high plus a configurable tick/ATR buffer.
- Bearish BOS: a completed 5m candle closes below the latest confirmed swing low minus the buffer.
- Wick-only breaches are not BOS.
- A swing level may be broken once for a given structural event; duplicate signals must be suppressed.
- **BOS vs CHoCH are mutually exclusive per completed bar and broken level (F2).** Which event a break produces depends on the structure state defined in §7.3. In a directional state the engine evaluates the **protected-level break first** (→ CHoCH), then a continuation break (→ BOS); it never emits both for the same bar/level event. If multiple same-direction levels are crossed by one bar, record the event against the level(s) qualified by the §7.3 state machine and suppress duplicate events for already-consumed level IDs.

### 7.3 CHoCH and the structure state machine (F1)

CHoCH is the first confirmed close through the **protected** opposing swing that contradicts the current established structure. It is produced by a deterministic state machine with state ∈ {NEUTRAL, BULL, BEAR} plus a protected swing reference. Do not infer CHoCH from a single candle colour or moving-average cross. Only confirmed 5m pivots (§7.1) are eligible, and a pivot is not available until its two right-side confirmation bars have closed. All breaks include the configured tick/ATR buffer from §7.2.

Rules:
- In **NEUTRAL**, the first qualifying bullish BOS establishes BULL; the first qualifying bearish BOS establishes BEAR. The establishing event is **BOS**, not CHoCH.
- **NEUTRAL double break (determinism rule).** If one completed candle's close satisfies **both** the bullish-break and bearish-break predicates simultaneously — which can occur only in the degenerate case where the latest confirmed swing low lies **above** the latest confirmed swing high, creating a price overlap band — then emit **no BOS**, remain **NEUTRAL**, and record `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK` with both level IDs. No directional priority is applied; the engine waits for unambiguous structure.
- On a bullish establishing BOS, set `protected_low` to the most recent confirmed swing low whose confirmation time is before the BOS bar close. On a bearish establishing BOS, set `protected_high` symmetrically. If no such pivot exists, do **not** establish directional state from that break; emit no structure event and wait for sufficient confirmed structure.
- In **BULL**, the protected level is the swing low selected at the most recent bullish BOS. It stays protected until a later bullish BOS updates it — **a newer swing low by itself does not replace it.** A completed close below `protected_low` (incl. buffer) emits **CHoCH**, changes state immediately to BEAR, and sets `protected_high` to the most recent confirmed swing high before the CHoCH close.
- In **BEAR**, apply the exact mirror: `protected_high` is selected at the most recent bearish BOS and stays fixed until that BOS updates it. A completed close above it emits CHoCH, flips state to BULL, and sets `protected_low` to the most recent confirmed swing low before the CHoCH close.
- After a CHoCH the new state is active immediately; a subsequent break in the new direction is classified as BOS and updates its protected swing. This avoids an undefined intermediate state.
- **Protected level unavailable after a CHoCH (determinism rule).** A CHoCH breaks the existing protected level, then selects a *new* protected level in the opposite swing set. If no qualifying opposite pivot exists before the CHoCH close, the CHoCH itself still stands and the new direction is retained, but the new protected level is set to **UNAVAILABLE**, the state flag `protection_pending` is set `true`, and `STRUCTURE_PROTECTION_PENDING` is recorded. While `protection_pending` is true in a directional state: (a) **no further CHoCH may be emitted** (there is no level to break); (b) a continuation **BOS** in the trend direction is still evaluated and, when it occurs, attempts to populate the protected level from the latest confirmed opposite pivot before that close — if one now exists, `protection_pending` is cleared, otherwise it remains pending. The engine never fabricates a protected level. `protection_pending` is the **canonical** boolean: it is initialized `false`, set `true` whenever a required protected reference is absent, and cleared `false` the moment a valid reference is assigned. The CHoCH guard is expressed as `protection_pending == false` (equivalently, the active protected reference is non-null — the two are kept equivalent by the pseudocode invariant below). Text and pseudocode therefore agree exactly.
- Persist pivot IDs, confirmation timestamps and the `protection_pending` flag, not just prices.

Reference pseudocode (normative):

```
state = NEUTRAL
protected_low = null
protected_high = null
protection_pending = false     # canonical flag; see invariant below

# INVARIANT: in a directional state, protection_pending == (active protected reference is null),
# where the active protected reference is protected_low in BULL and protected_high in BEAR.
# The two checks are therefore equivalent; protection_pending is the canonical one.

for each completed 5m bar, chronologically:
    use only pivots confirmed before this bar closes
    broke_high = close breaks latest confirmed swing high (incl. buffer)
    broke_low  = close breaks latest confirmed swing low  (incl. buffer)

    if state == NEUTRAL:
        if broke_high and broke_low:                 # degenerate overlap: swing_low above swing_high
            emit STRUCTURE_AMBIGUOUS_DOUBLE_BREAK     # remain NEUTRAL, no BOS, no priority
        else if broke_high:
            candidate = latest confirmed swing low before this close
            if candidate exists:
                emit BOS_UP; state = BULL; protected_low = candidate; protection_pending = false
            # else: no anchor -> remain NEUTRAL, emit nothing
        else if broke_low:
            candidate = latest confirmed swing high before this close
            if candidate exists:
                emit BOS_DOWN; state = BEAR; protected_high = candidate; protection_pending = false

    else if state == BULL:
        if (not protection_pending) and close breaks protected_low:   # protected break evaluated first
            emit CHOCH_DOWN(protected_low); state = BEAR
            protected_high = latest confirmed swing high before this close
            if protected_high == null:
                protection_pending = true; emit STRUCTURE_PROTECTION_PENDING
            else:
                protection_pending = false
        else if broke_high:                                           # continuation
            emit BOS_UP
            protected_low = latest confirmed swing low before this close
            protection_pending = (protected_low == null)              # found -> false; still absent -> true

    else if state == BEAR:
        if (not protection_pending) and close breaks protected_high:
            emit CHOCH_UP(protected_high); state = BULL
            protected_low = latest confirmed swing low before this close
            if protected_low == null:
                protection_pending = true; emit STRUCTURE_PROTECTION_PENDING
            else:
                protection_pending = false
        else if broke_low:
            emit BOS_DOWN
            protected_high = latest confirmed swing high before this close
            protection_pending = (protected_high == null)
```

Determinism notes (Gate 2 fixtures):
- The only way one completed candle can satisfy both break predicates is the degenerate overlap where the latest confirmed swing low sits above the latest confirmed swing high. It resolves to `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK` (no BOS, remain NEUTRAL) — **not** a directional priority. A dedicated fixture must cover it.
- A CHoCH whose new opposite pivot does not yet exist resolves to `protection_pending` with `STRUCTURE_PROTECTION_PENDING`: the flip stands, no further CHoCH fires, and the next continuation BOS repopulates the protected level. A dedicated fixture must cover this, including the subsequent BOS that clears the flag.

### 7.4 Displacement

A qualifying displacement candle or sequence must:
- Close in the direction of the structural break.
- Have body/range strength above a configurable ATR(14)-normalized threshold.
- Close beyond the relevant swing level for BOS.
- Optionally show time-of-day adjusted volume expansion as a quality modifier, not a mandatory assumption.

Initial test threshold: candle body >= 1.0 × ATR(14) is deliberately strict and must be sensitivity-tested; compare 0.7, 1.0 and 1.3 ATR in research without choosing the best value on the final holdout.

### 7.5 Order block

- **Anchor and lookback (F3).** For a qualifying displacement sequence D1…Dn that causes BOS, the anchor is the **first candle of the sequence, D1** — not the later candle whose close confirms BOS. Search only the **five completed candles immediately preceding D1** (configurable lookback, provisional default 5). Do not include D1 or any later displacement/BOS-confirmation candle in the search window.
- Bullish OB: the most recent **bearish** candle in that pre-D1 window. Bearish OB: the most recent **bullish** candle in that pre-D1 window.
- Initial zone boundary: full high-low range of the OB candle. Store body-only boundaries as an alternate model for sensitivity tests.
- Each zone stores: selected OB candle ID, D1 bar ID, displacement sequence IDs, linked BOS event ID, creation time, direction, proximal/distal boundaries, displacement metrics, lookback/config version, optional FVG confluence and state.
- If no qualifying opposite candle exists within the pre-D1 window, no OB is created.

### 7.6 Fair value gap

For three consecutive completed candles A, B, C:
- Bullish FVG if low(C) > high(A); zone = [high(A), low(C)].
- Bearish FVG if high(C) < low(A); zone = [high(C), low(A)].
- Minimum gap size is configurable and normalized by ATR/tick size.
- Record creation and fill/mitigation state. FVG is a confluence feature, not an independent trade trigger.

### 7.7 Liquidity sweep

A sweep may reference either a confirmed strict swing (§7.1) or a confirmed equal-extreme liquidity pool (§7.1, F4). A sweep occurs when price trades beyond the reference level — a swing high/low, or a pool reference price — by a configurable sweep buffer and the same completed candle, or a defined subsequent completed candle within the configured reclaim window, closes back through the reference level. Store the swept level, whether its source was a **swing or a pool**, the breach extreme, reclaim close and timestamps. Do not label every wick as a sweep.

### 7.8 Mitigation and invalidation

- First touch: price range intersects the OB zone after creation.
- Partial mitigation: price enters but does not traverse the entire zone.
- Full mitigation: price traverses to the distal boundary.
- Invalidated bullish OB: completed 5m close below distal boundary minus configured buffer.
- Invalidated bearish OB: completed 5m close above distal boundary plus configured buffer.
- A zone's state transitions are one-way and timestamped. Never reset an invalidated zone to fresh.

### 7.9 Entry trigger

Research baseline:
- Bullish: price revisits an active bullish OB, then a completed 5m candle closes bullish and breaks the immediately preceding completed candle high; entry is considered on the next bar/available executable quote, not retroactively at the signal close.
- Bearish: inverse.
- Require no invalidation before entry and ensure the entry has not moved beyond the maximum permitted distance from the zone.
- **Maximum entry distance (F10).** Express the maximum permitted entry distance from the OB zone as a multiple of 5m ATR(14), stored as numeric `max_entry_distance_atr` config. Use **0.5 ATR** only as an initial research value for fixtures/sensitivity testing, not a validated production threshold. Persist the ATR value, its calculation timestamp, the zone boundary and the measured distance used for each decision.
- Compare OB midpoint entry, proximal-boundary entry and confirmation entry as separate test variants. Do not combine them into one undocumented rule.

### 7.10 Stop and target

- Structural stop: beyond the OB distal boundary plus a configurable volatility/tick buffer.
- If the structural stop is too wide relative to ATR or available contract liquidity, reject the setup.
- Primary target: next opposing confirmed swing/liquidity level, if present and objectively identified.
- **Reward/risk is instrument-type aware (F6).** The underlying structural R:R (initial threshold 2.0 after estimated costs) is the binding gate for the **futures** path only. For a **long option**, the underlying setup is directional context only; its price-based R:R does not map to the option's premium R:R, so the underlying R:R must not approve or reject the option. The binding option R:R gate is applied at contract selection (§9.3). Keep 2.0 provisional and validate separately for futures and long options.
- If no defensible target exists, do not invent a fixed target; mark the setup ineligible or use a separately tested ATR target model.
- Recompute reward/risk using the actual derivative instrument's executable bid/ask and costs at contract-selection stage.

## 8. Tradability score (5m)

Evaluate the six directional candidates independently. Initial weights are provisional:

| Component | Weight |
|---|---:|
| Freshness and entry proximity | 20 |
| OB quality and confluence | 20 |
| BOS/CHoCH confirmation | 15 |
| Net reward/risk potential | 20 |
| Underlying liquidity / execution quality | 15 |
| Stop feasibility / volatility | 10 |
| **Total** | **100** |

Initial hard gates:
- Tradability score >= 70/100.
- Net expected R multiple >= 2.0, applied **by instrument type (F6)**: on the underlying/futures R:R for the futures path; for the long-option path this gate is deferred to contract selection (§9.3) on the option's own premium-based R:R. Do not gate an option candidate on the underlying's price-based R:R.
- Active, uninvalidated setup.
- No stale/missing signal-critical data.
- Valid entry, stop and target.
- At least one eligible derivative contract passes contract-level liquidity and risk checks.

Select the highest score across bullish and bearish candidates. If none passes every gate, return NO_TRADE with reason codes such as NO_DIRECTIONAL_EDGE, NO_FRESH_SETUP, OB_INVALIDATED, ENTRY_TOO_EXTENDED, RR_BELOW_MINIMUM, CONTRACT_UNAVAILABLE, CONTRACT_ILLIQUID, DATA_STALE, MARKET_RESTRICTION, SESSION_CLOSED. While the system is not LIVE (§4A), suppression is reported with SYSTEM_NOT_LIVE / SYNC_INCOMPLETE, and a constituent in a confirmed no-data condition carries SYMBOL_HALTED / SYMBOL_NO_TRADE_BUCKET.

## 9. Derivative contract selection

The underlying signal and derivative contract are distinct objects. Preserve both IDs and their own price/volume histories.

### 9.1 Futures

- Select only active FUTSTK contracts present in the current instrument master.
- Prefer the nearest expiry with sufficient liquidity, unless expiry/rollover risk makes the next contract more suitable.
- Check bid/ask spread, traded volume, OI, market depth where available, basis to underlying, lot size, quantity freeze, margin and broker RMS restrictions.
- Futures may express bullish or bearish underlying views by going long or short, subject to broker/product permissions and applicable exchange controls.
- Do not hardcode expiry dates or lot sizes.

### 9.2 Options

- Bullish underlying view maps to CE candidates; bearish view maps to PE candidates.
- Initially evaluate long option positions (buy CE / buy PE) only. Option writing/short options are explicitly out of initial scope due to materially different margin, tail-risk and execution requirements; owner approval is required to add them.
- Candidate strikes: ATM and a configurable nearby-strike range; compare delta, spread, volume, OI, premium, IV, theta and days to expiry.
- Reject contracts with stale quotes, insufficient volume/OI, wide spread, abnormal premium or inadequate time-to-expiry under configured rules.
- Option premium stop/target must be derived from option price behaviour and/or a tested underlying-trigger exit rule. Never copy the underlying price stop directly into option premium.
- Include expiry-day and physical-settlement/exercise risk controls. Contract availability and settlement rules must be loaded from current exchange specifications.

### 9.3 Contract score

A separate contract score should compare eligible futures/options, using:
- Executable spread and depth.
- Volume and OI.
- Expected slippage.
- Margin/capital efficiency.
- For options: delta suitability, theta decay, IV and expiry risk.
- Broker RMS and exchange restrictions.

**Binding option R:R gate (F6).** The long-option R:R gate is applied here, using the option's own executable premium entry/exit assumptions (bid/ask, slippage, costs) or a separately specified and empirically validated underlying-trigger/option-exit model. The option model must produce its own risk and reward values; never copy the underlying stop distance into premium. Until a defensible option-specific R:R estimate exists, the option contract is **ineligible** and the final outcome is NO_TRADE for that instrument path — do not silently waive the gate.

Do not compare raw futures and option premium prices as if they were equivalent. If no contract is suitable, the underlying remains a directional candidate but the final result is NO_TRADE.

## 10. Risk, costs and signal lifecycle

### 10.1 Risk

- Position sizing is based on configured maximum rupee risk per trade divided by estimated per-lot loss to stop, rounded down to valid lots.
- Never size by a fixed number of lots independent of stop distance.
- Enforce configurable max daily loss, max concurrent positions, max trades/session and cooldown after loss.
- No averaging down or adding to a losing position in the initial scope.
- No automatic order placement in v0.1.

Risk amount, daily loss limit, concurrent position limit and square-off time require owner approval before live alerts can be promoted as executable trade plans.

### 10.2 Costs

Model costs instrument-by-instrument and side-by-side:
- Brokerage according to the user's actual plan.
- Exchange transaction charges.
- SEBI charges.
- GST on applicable charges.
- STT with current instrument/side-specific rates.
- Stamp duty where applicable.
- Slippage and spread crossing.
- Any applicable other statutory levies.

Keep cost schedules versioned by effective date. Do not hardcode tax rates permanently. Use actual broker contract notes or verified current schedules for calibration.

### 10.3 Signal lifecycle

Persist explicit transitions:
CREATED → PENDING_ENTRY → TRIGGERED → ACTIVE → (STOPPED_OUT | TARGET_REACHED | INVALIDATED | EXPIRED | CANCELLED).

A signal must not silently disappear when a higher-ranked candidate appears. A new candidate may replace the dashboard's "best current opportunity" but must not rewrite an existing signal's history. Store event time, reason, bar IDs, score components, strategy version, config hash, data-source IDs and outcome.

## 11. Backtesting and validation

### 11.1 Shared engine

Live and backtest must call the same feature, structure, scoring, eligibility and signal-state code. Only the data adapter and execution simulator differ. The backtest must replay bars in chronological order and expose only information available at each event time.

### 11.2 Bias controls

- Point-in-time Nifty 50 membership and point-in-time F&O contract availability.
- Historical contract metadata including expiry, lot size and strike scheme.
- No look-ahead in pivot confirmation, OB creation, FVG, indicator warm-up or ranking.
- No survivorship bias from applying today's constituents to all past dates.
- No use of future option Greeks/IV/OI.
- Chronological train/validation/test split; final holdout remains untouched during feature/weight tuning.
- Record all parameter trials to expose multiple-testing risk.

If reliable historical constituent or derivative contract history is unavailable, label the affected test as biased/limited. Do not call it an unbiased backtest.

### 11.3 Execution simulation

- Signal generated at completed 5m close; fill no earlier than next executable event/bar under the selected fill model.
- Use bid/ask or conservative spread/slippage model; do not assume every signal fills at candle close.
- Model gaps, partial fills, liquidity limits, lot sizes, quantity freeze and expiry/rollover.
- For options, backtest the actual historical option contract, not a synthetic payoff inferred solely from underlying candles. **This is contingent on the Gate 0 expired-option history audit (F7).** If sufficient historical OHLC for expired individual-stock option contracts is unavailable from SmartAPI, do not claim an unbiased historical options backtest: mark the affected options backtest limited/unavailable (§11.2) and validate the options path **prospectively** through Gate 5 paper observation, unless a separately approved data source is added.

### 11.4 Required metrics

Report net-of-cost:
- Trade count and exposure.
- Expectancy per trade in INR and R.
- Profit factor.
- Maximum drawdown and recovery.
- Win rate and average win/loss.
- MAE/MFE.
- Sharpe/Sortino only with methodology and caveats.
- Performance by year, month, direction, regime, sector, time of day, instrument type and expiry proximity.
- Slippage sensitivity and cost sensitivity.
- Benchmark against a simple baseline and a no-signal/no-trade baseline.

Do not declare success using win rate alone. No numeric pass threshold is approved yet; owner must approve acceptance criteria after baseline results and realistic cost assumptions are available.

## 12. Persistence and reproducibility

Every generated signal and backtest run must record:
- Strategy semantic version and git commit.
- Full config snapshot and cryptographic hash.
- Underlying and derivative contract identifiers.
- Input candle IDs / data snapshot reference.
- Feature values and component score contributions.
- Eligibility pass/fail and reason codes.
- Entry, stop, target, fill assumptions and cost schedule version.
- Lifecycle events and final outcome.

Same input data + same code version + same config must reproduce the same result.

## 13. Dashboard requirements

### Main scanner
- All 50 Nifty constituents, symbol, LTP, change %, 15m trend, RS, RVOL, bullish score, bearish score, data health and F&O availability.
- Top 3 bullish and top 3 bearish panels.
- Highest tradability panel or NO TRADE with explanation.
- Last update time and connection/data health indicator.
- **Live Readiness banner (§4A):** prominent system state — `LIVE` vs `CATCHING UP` / `DEGRADED — NOT LIVE` — with current recovery stage, the common universe watermark, and the count of constituents blocking LIVE. Actionable panels (shortlists, best pick) are hidden or disabled while not LIVE.

### Instrument detail window
- 15m and 5m chart views.
- OB zones with state and timestamps.
- Confirmed swing highs/lows, BOS, CHoCH, FVG and liquidity sweeps.
- Entry trigger, invalidation, stop, target and net R:R.
- Underlying-to-derivative mapping and eligible contract comparison.
- Score breakdown, reasons for rejection and data-quality warnings.

### Audit / research
- Signal journal and lifecycle.
- Config/version history.
- Backtest runs and report comparison.
- Data gaps and feed status.
- No order-entry controls in v0.1.

## 14. Open decisions requiring owner approval

1. Exact session start/no-trade window, last-entry time, forced square-off and signal expiry.
2. Risk per trade, max daily loss, max concurrent trades and cooldown.
3. Whether final production preference should be futures-first, options-first, or let contract score choose between them. Research baseline: support both; validate futures first; options buying as a separate model.
4. Whether options buying only is accepted for v0.1; option writing remains excluded by default.
5. Exact data-retention and historical test period, subject to actual SmartAPI coverage and point-in-time reference data.
6. Backtest acceptance thresholds and benchmark.
7. Frontend/backend/database/deployment stack.
8. Exact indicator/SMC parameter values after sensitivity analysis, not intuition.

## 15. Implementation gates

- **Gate 0 — Data audit:** Prove SmartAPI login, streaming, candle history, instrument master refresh, rate limiting, reconnect and persistence. No signals. **Must additionally (F7, F8):** (a) test actual historical OHLC retrieval for a documented sample of **expired** individual-stock option contracts across expiries, strikes and dates, including contracts no longer in the current instrument master — recording requested vs returned candles, coverage dates, missing intervals, symbol/token resolution method, API errors/rate limits and reproducibility; and (b) measure usable, gap-audited 5m/15m **volume** history per instrument (including recently added constituents and holiday/missing-bar sessions) to settle the RVOL baseline sample counts of §6.1. These Gate 0 findings resolve F7/F8; they are not Gate 2 blockers. **Must also prove the §4A gap-recovery / Live Readiness Gate**, with acceptance tests for: (i) app starts ~30 min late mid-session; (ii) cold start after a long absence / next trading day, where calendar gaps are not treated as missing bars; (iii) WebSocket disconnect while running, with bars arriving during REST backfill (REST↔stream seam closed); (iv) restart during an incomplete recovery run (idempotent resume); (v) duplicate, out-of-order, missing, stale and conflicting overlap candles; (vi) API rate-limit / partial historical response / unavailable historical range; (vii) one constituent incomplete while the other 49 are current (and the §4A.4 halt vs unverified-gap distinction); (viii) all 50 symbols × both timeframes synchronize, indicators warm, and only then LIVE is granted; (ix) a new gap or stale feed after LIVE immediately revokes readiness and blocks new signals. **Acceptance:** in every incomplete, ambiguous or failed recovery case the system stays visibly NOT LIVE and emits no actionable signal; LIVE is reached only after validated, gap-free data through a common completed-bar watermark and successful warm-up. **Must empirically prove with SmartAPI** (do not assume): the latency between a candle's close and its availability in the historical endpoint (the window the WS buffer must cover), the real per-cold-start request budget for 50×2 instrument-timeframes under the 3 req/s · 180/min limit, instrument-master/token refresh correctness, and WS-to-canonical-bar volume semantics. **Must also prove the §4A.4 no-data classification mechanism** before `halt_blocks_global_live` may be set `false`: whether an authoritative exchange/broker halt-status source exists and is reliable; SmartAPI's documented empty/zero-trade-interval semantics on the historical endpoint; and that the historical-bracket + healthy-WS-silence conjunction can be observed and logged. **Classification fixtures (positive pass only when evidence criteria are met; all others stay UNKNOWN → block):** confirmed halt (authoritative status); confirmed zero-trade bucket (bracketed history + healthy WS silence); and negative cases that must NOT pass — API partial response, WS disconnect, invalid/stale token, delayed historical publication, and ambiguous no-data. Assert per-instrument-and-per-timeframe scope and the 5m→15m aggregation contract.
- **Gate 1 — Scanner:** Build 50-stock table and 15m features; test data quality and ranking reproducibility. Include the §6.2 neutral band (F5). RVOL scoring stays disabled until the F8 data audit and an approved missing-feature policy exist.
- **Gate 2 — Deterministic structure:** Implement pivots/BOS/CHoCH/OB/FVG as pure functions with hand-checked fixtures and no-look-ahead tests. **Fixtures must cover both directions and (F1–F4):** NEUTRAL establishment, protected-swing selection, CHoCH reversal and immediate re-arming, multi-candle displacement OB anchoring on D1, equal-extreme liquidity pools, no-look-ahead pivot confirmation, and the two §7.3 determinism cases — `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK` (degenerate overlap in NEUTRAL: no BOS, stay NEUTRAL) and `STRUCTURE_PROTECTION_PENDING` (CHoCH with no available new protected pivot, plus the later continuation BOS that clears the flag). Fixtures must assert the `protection_pending` flag transitions (false→true on the CHoCH, true→false on the repopulating BOS) in both the BULL→BEAR and BEAR→BULL directions, not only the emitted event codes.
- **Gate 3 — Tradability and derivative mapping:** Add 5m entry state machine, contract eligibility and risk/cost estimates.
- **Gate 4 — Historical replay:** Shared engine, realistic execution, bias controls and out-of-sample reports.
- **Gate 5 — Paper observation:** Live shadow signals without order placement; compare live events with replay expectations.
- **Gate 6 — Live execution:** **Out of scope for this project.** The application never executes orders; the owner places any trades manually. No execution gate is built. (Retained here only to state explicitly that automated execution is not part of the system.)

## 16. Definition of done for strategy v0.2

The strategy specification is implementable when:
- All owner decisions in section 14 needed for the relevant gate are resolved.
- Every feature and SMC event has deterministic inputs, timestamps and state transitions.
- Unit tests cover pivots, BOS/CHoCH, OB, FVG, sweeps, mitigation, invalidation, ranking, missing data and session boundaries.
- Look-ahead tests prove pivots and signals are not available before confirmation.
- Live and replay use the same strategy code.
- Every NO_TRADE and rejected candidate has reason codes.
- Results can be reproduced from stored data/config/code versions.

**No profitability claim is made by this document. All scoring weights, thresholds and setup rules remain hypotheses until independently validated.**

## 17. Changelog — v0.1 → v0.2

Incorporates the Task 001 review/revision dispositions (owner-approved 2026-11-04). Sources: `comms/claude/001-strategy-spec-review.md`, `comms/chatgpt/001-strategy-spec-revision.md`.

| Finding | Change | Section |
|---|---|---|
| F1 | Added deterministic CHoCH structure state machine (NEUTRAL/BULL/BEAR, protected swing, normative pseudocode). | §7.3 |
| F2 | BOS vs CHoCH made mutually exclusive and state-dependent; protected-level break evaluated before continuation. | §7.2, §7.3 |
| F3 | Order-block anchor fixed to first displacement candle (D1); lookback is the 5 candles before D1. | §7.5 |
| F4 | Retained strict swings; added separate equal-extreme liquidity-pool detector (one-tick tolerance, median reference); sweeps may reference swing or pool. | §7.1, §7.7 |
| F5 | Defined neutral band = 5 score points with explicit dual-list rule. | §6.2 |
| F6 | R:R gate made instrument-type aware; option R:R deferred to contract selection on premium, no silent waiver. | §7.10, §8, §9.3 |
| F7 | Expired-option historical backtest made contingent on a Gate 0 audit; fallback to prospective Gate 5 validation. | §11.3, §15 |
| F8 | RVOL baseline defined (median of same bucket over prior 20 sessions, min 10; unavailable≠zero) and Gate-0 gated. | §6.1, §15 |
| F9 | Named EMA 9/21/50 as the provisional research set, distinct from index regime EMA 20/50. | §6 |
| F10 | Maximum entry distance expressed as a 5m ATR(14) multiple (`max_entry_distance_atr`, initial 0.5). | §7.9 |
| F11 | Added explicit WARMUP regime state that suppresses labels and countertrend ranking until inputs are valid. | §5 |

All values introduced here remain provisional research parameters and must be sensitivity-tested; none is an approved production threshold or a profitability claim.

### Post-approval corrections (2026-11-04)

Owner-directed corrections after v0.2 approval. Smallest-necessary changes; no unrelated parameters altered.

| Item | Change | Section |
|---|---|---|
| §7.3-C1 | Replaced the NEUTRAL double-break "bullish priority" tie-break (which was in fact impossible under close-based breaks) with explicit `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK`: on the degenerate overlap (latest swing low above latest swing high) emit no BOS and remain NEUTRAL. | §7.2 inapplicable; §7.3 rules, pseudocode, fixtures |
| §7.3-C2 | Made the protected-level-unavailable-after-CHoCH behaviour explicit and consistent between prose and normative pseudocode: CHoCH stands, direction retained, protected level = UNAVAILABLE with `protection_pending`/`STRUCTURE_PROTECTION_PENDING`; no further CHoCH until a continuation BOS repopulates the level. | §7.3 rules, pseudocode, fixtures |
| §7.3-C2b | Precision follow-up (ChatGPT review): made `protection_pending` an explicit canonical boolean — initialized `false`, set/cleared on every CHoCH and continuation-BOS path, with a stated invariant that it equals "active protected reference is null". CHoCH guard expressed as `protection_pending == false`. Fixtures now assert the flag transitions in both directions, not only event codes. | §7.3 rules, pseudocode, §15 fixtures |
| §15 | Added Gate 2 fixtures for both new cases. | §15 |
| Timeframe | Finalized 5m/15m as the sole configuration (no parallel 1/5 mode). Rationale and trade-offs recorded in `DECISION_LOG.md` DEC-005 and `comms/claude/003-timeframe-decision-review.md`. 1m retained only as a possible Gate 5 execution-timing experiment, never a parallel mode. | A-03, DEC-005 |

New structure-engine event codes introduced: `STRUCTURE_AMBIGUOUS_DOUBLE_BREAK`, `STRUCTURE_PROTECTION_PENDING`. These are persisted structure events (§12), distinct from §8 NO_TRADE reason codes.

| §4A | Added **Startup gap recovery and Live Readiness Gate** (owner requirement 2026-11-04): explicit readiness states, idempotent recovery sequence, hard no-live/no-signal rule, audit trail; dashboard Live Readiness banner (§13); Gate 0 recovery acceptance tests + SmartAPI proof items (§15); suppression/halt reason codes (§8). Includes a flagged co-owner decision (§4A.4). | §4A, §8, §13, §15 |
| §4A.4-rev | **Joint co-owner resolution** after ChatGPT's challenge: default changed to fail-closed `halt_blocks_global_live = true` (an absent candle does not prove a halt/zero-trade); added a testable no-data **classification contract** (authoritative halt status; bracketed-history + healthy-WS-silence for zero-trade; per-instrument/timeframe scope + 5m→15m aggregation; timeout→NOT LIVE) and Gate 0 positive/negative classification fixtures and a confirmation-mechanism proof requirement. Flipping to `false` needs Gate 0 evidence + both co-owners' agreement. | §4A.4, §15 |

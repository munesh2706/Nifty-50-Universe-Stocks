# Strategy Specification — v0.1 (Research Baseline)

- **Status:** Proposed technical baseline; scoring thresholds and SMC parameters are not yet empirically validated.
- **Owner:** Munesh
- **Market data provider:** Angel One SmartAPI
- **Underlying universe:** Current Nifty 50 constituents
- **Primary horizon:** Intraday
- **Scanner timeframe:** 15-minute
- **Setup/entry-analysis timeframe:** 5-minute
- **Derivative scope:** NSE individual-stock futures and options, subject to current contract availability and broker permissions
- **Execution scope:** Decision support and alerts only. Live order placement is out of scope until separately approved.

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

Regime is a context feature, not an absolute direction veto. Countertrend candidates may rank, but should require stronger structure/entry confirmation and can be disabled by configuration. Regime thresholds are provisional and must be tested.

## 6. Underlying directional ranking (15m)

Compute separate BULL_SCORE and BEAR_SCORE, each in [0,100]. The weights below are provisional research weights.

| Component | Weight | Example evidence |
|---|---:|---|
| Trend alignment | 25 | EMA 9/21/50 ordering, price vs VWAP, 15m slope |
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
- Indicator warm-up requirements must be satisfied before a stock is eligible.
- Avoid double-counting correlated indicators. Preserve feature-level contributions for explanation.

### 6.2 Ranking and eligibility

Apply hard eligibility filters first:
- Healthy, synchronized data.
- Valid 15m trend/indicator warm-up.
- Minimum underlying liquidity and acceptable spread/impact-cost proxy.
- No exchange/broker trading restriction or price-band condition that makes execution impractical.
- For derivative tradability, at least one currently active and broker-accessible stock derivative contract must exist.

Then rank eligible stocks. Initial directional score threshold: 65/100, provisional. Show up to three per direction; promote the next eligible name if a higher-ranked name fails a hard gate. A stock may appear in both lists only if the scoring model genuinely produces qualifying scores in both directions; otherwise enforce a configurable neutral band to prevent contradictory simultaneous labels.

## 7. Deterministic market structure / SMC definitions (5m)

These are initial codeable definitions for research. They are not discretionary chart annotations and must not be altered without a versioned strategy change.

### 7.1 Swing points

A swing high at bar i is confirmed when its high is strictly greater than the highs of the two preceding and two following completed bars. A swing low is the inverse. The pivot becomes usable only after both right-side confirmation bars have closed. Store pivot_time and confirmation_time separately to prevent look-ahead.

### 7.2 BOS

- Bullish BOS: a completed 5m candle closes above the latest confirmed swing high plus a configurable tick/ATR buffer.
- Bearish BOS: a completed 5m candle closes below the latest confirmed swing low minus the buffer.
- Wick-only breaches are not BOS.
- A swing level may be broken once for a given structural event; duplicate signals must be suppressed.

### 7.3 CHoCH

CHoCH is the first confirmed close through the protected opposing swing that contradicts the current established structure. Define the current structure state explicitly (BULL, BEAR, NEUTRAL); do not infer CHoCH from a single candle colour or moving-average cross.

### 7.4 Displacement

A qualifying displacement candle or sequence must:
- Close in the direction of the structural break.
- Have body/range strength above a configurable ATR(14)-normalized threshold.
- Close beyond the relevant swing level for BOS.
- Optionally show time-of-day adjusted volume expansion as a quality modifier, not a mandatory assumption.

Initial test threshold: candle body >= 1.0 × ATR(14) is deliberately strict and must be sensitivity-tested; compare 0.7, 1.0 and 1.3 ATR in research without choosing the best value on the final holdout.

### 7.5 Order block

- Bullish OB: the last bearish candle within a bounded lookback (initially up to five completed candles) before the qualifying bullish displacement that causes bullish BOS.
- Bearish OB: the last bullish candle in the corresponding bearish sequence.
- Initial zone boundary: full high-low range of the OB candle. Store body-only boundaries as an alternate model for sensitivity tests.
- Each zone stores source candle, creation time, direction, proximal/distal boundaries, linked BOS event, displacement metrics, optional FVG confluence and state.
- If no qualifying opposite candle exists within the lookback, no OB is created.

### 7.6 Fair value gap

For three consecutive completed candles A, B, C:
- Bullish FVG if low(C) > high(A); zone = [high(A), low(C)].
- Bearish FVG if high(C) < low(A); zone = [high(C), low(A)].
- Minimum gap size is configurable and normalized by ATR/tick size.
- Record creation and fill/mitigation state. FVG is a confluence feature, not an independent trade trigger.

### 7.7 Liquidity sweep

A sweep occurs when price trades beyond a confirmed swing high/low by a configurable buffer and the same completed candle or a defined subsequent completed candle closes back inside the prior level. Store the swept level, breach extreme, reclaim close and timestamps. Do not label every wick as a sweep.

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
- Compare OB midpoint entry, proximal-boundary entry and confirmation entry as separate test variants. Do not combine them into one undocumented rule.

### 7.10 Stop and target

- Structural stop: beyond the OB distal boundary plus a configurable volatility/tick buffer.
- If the structural stop is too wide relative to ATR or available contract liquidity, reject the setup.
- Primary target: next opposing confirmed swing/liquidity level, if present and objectively identified.
- Require expected reward/risk >= 2.0 after estimated trading costs for the initial candidate gate.
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
- Net expected R multiple >= 2.0.
- Active, uninvalidated setup.
- No stale/missing signal-critical data.
- Valid entry, stop and target.
- At least one eligible derivative contract passes contract-level liquidity and risk checks.

Select the highest score across bullish and bearish candidates. If none passes every gate, return NO_TRADE with reason codes such as NO_DIRECTIONAL_EDGE, NO_FRESH_SETUP, OB_INVALIDATED, ENTRY_TOO_EXTENDED, RR_BELOW_MINIMUM, CONTRACT_UNAVAILABLE, CONTRACT_ILLIQUID, DATA_STALE, MARKET_RESTRICTION, SESSION_CLOSED.

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
- For options, backtest the actual historical option contract, not a synthetic payoff inferred solely from underlying candles.

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

- **Gate 0 — Data audit:** Prove SmartAPI login, streaming, candle history, instrument master refresh, rate limiting, reconnect and persistence. No signals.
- **Gate 1 — Scanner:** Build 50-stock table and 15m features; test data quality and ranking reproducibility.
- **Gate 2 — Deterministic structure:** Implement pivots/BOS/CHoCH/OB/FVG as pure functions with hand-checked fixtures and no-look-ahead tests.
- **Gate 3 — Tradability and derivative mapping:** Add 5m entry state machine, contract eligibility and risk/cost estimates.
- **Gate 4 — Historical replay:** Shared engine, realistic execution, bias controls and out-of-sample reports.
- **Gate 5 — Paper observation:** Live shadow signals without order placement; compare live events with replay expectations.
- **Gate 6 — Live execution:** Not authorised by this specification. Requires separate owner approval, broker/RMS checks and operational safeguards.

## 16. Definition of done for strategy v0.1

The strategy specification is implementable when:
- All owner decisions in section 14 needed for the relevant gate are resolved.
- Every feature and SMC event has deterministic inputs, timestamps and state transitions.
- Unit tests cover pivots, BOS/CHoCH, OB, FVG, sweeps, mitigation, invalidation, ranking, missing data and session boundaries.
- Look-ahead tests prove pivots and signals are not available before confirmation.
- Live and replay use the same strategy code.
- Every NO_TRADE and rejected candidate has reason codes.
- Results can be reproduced from stored data/config/code versions.

**No profitability claim is made by this document. All scoring weights, thresholds and setup rules remain hypotheses until independently validated.**

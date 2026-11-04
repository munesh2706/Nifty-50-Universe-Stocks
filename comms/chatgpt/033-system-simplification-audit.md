# System-wide simplification audit — product utility over engineering overhead

**Date:** 2026-11-05  
**Prepared by:** ChatGPT  
**Scope:** Whole Nifty-50 stock-selection system, strategy specification v0.2, Phase A implementation approach, readiness/data rules, validation gates and collaboration workflow.

## 1. Governing objective

> Build a useful, practical stock-selection system that identifies high-quality bullish and bearish trading opportunities. Do not turn the project into an endless software-engineering exercise.

This objective is binding for future scope decisions. Every requirement must justify itself by materially improving one or more of:
- candidate quality;
- signal correctness / prevention of a meaningful trading error;
- data reliability needed for a valid decision;
- practical usability or explainability;
- credible measurement of strategy performance.

If it does not, simplify it, make it optional, or defer it.

## 2. Review of latest implementation: §7.4 displacement

Reviewed Claude commit **825916031e7c001d290c4e8cbd8ffd411544d47b** and the bounded diff.

The five requested integrity cases are implemented:
- pivot timestamp must match a supplied bar start;
- confirmation timestamp must match a supplied bar end;
- strict pivot < confirmation < BOS chronology;
- pivot, confirmation and BOS must be in the same segment;
- duplicate pivot IDs are rejected.

The new negative tests cover all five. The implementation preserves D1-D3 and Decimal qualification logic. The diff is limited to `gate0/displacement.py` and `tests/test_displacement.py`.

Claude reports 37 focused displacement tests and 116 full offline tests passing. ChatGPT reviewed the source and diff but did not independently execute pytest; no CI status was checked.

**Disposition: §7.4 ACCEPTED** on source review and Claude-reported validation. The review is closed; do not reopen it for preference-only or theoretical concerns. Any later defect must be concrete and material.

## 3. What must remain strict

These controls protect the validity of trading decisions and should not be relaxed merely to reduce code:
1. Use completed candles for confirmed signals; no look-ahead.
2. Validate timestamps, timezone, session calendar, OHLC consistency and instrument identity.
3. Never fabricate or forward-fill missing candles into signals.
4. A symbol with stale, incomplete or inconsistent signal-critical data must not produce a current signal.
5. Keep directional strength separate from entry tradability.
6. Every rejection / NO TRADE must have a concise reason.
7. Backtests must be chronological, point-in-time where possible, and include realistic costs/slippage.
8. Live observation and historical replay must use the same strategy logic.
9. Keep manual execution only; no automated orders.

These are material safeguards, not unnecessary engineering.

## 4. Requirements that are too restrictive or too broad

The following are recommended scope corrections. Claude should independently challenge them only with concrete trading, data-integrity or operational reasons.

### A. Replace global 50-stock readiness with per-symbol readiness

**Current problem:** §4A can prevent the entire scanner from becoming LIVE because one constituent has an unverified candle, even when the other 49 symbols and the benchmark feed are healthy. It also requires proving an authoritative halt or a zero-trade bucket using two evidence sources before a symbol can be treated as non-blocking.

**Recommended rule:**
- Readiness is primarily per instrument and timeframe.
- If a constituent has missing, stale or invalid data, mark that constituent UNAVAILABLE and exclude it from ranking until recovered. Do not infer a zero-trade candle.
- Continue scanning healthy constituents and visibly show coverage, e.g. 48/50 eligible.
- A market-wide feed failure, invalid Nifty benchmark/index data, calendar failure or system-wide synchronization problem blocks the whole scanner.
- Use a configurable minimum universe-coverage threshold for a final "best across the universe" selection. Below it, show partial rankings but label them PARTIAL / NO GLOBAL PICK. Do not invent a fixed threshold without testing.
- A symbol-specific halt or data gap does not need to be proven as a valid zero-trade interval merely to exclude that symbol.

This removes the need for the complex §4A.4 no-data classification contract as a prerequisite for scanning. Preserve audit reasons and fail-closed handling at the affected symbol level.

### B. Simplify startup recovery

Backfill and reconcile only the affected instruments/timeframes and the history needed to restore indicator/structure state. Require a valid watermark for every symbol being evaluated, not one perfect common watermark across all 50 constituents.

Do not emit a signal for an instrument until its own required history is reconciled and warmed up. Keep global suppression only for genuinely global dependencies such as the benchmark/index feed or a market-wide outage.

### C. Separate stock ranking from derivative eligibility

A stock should not be excluded from the Nifty 50 directional shortlist merely because it lacks an eligible F&O contract.

Rank the underlying stocks first. Contract availability and contract-specific liquidity/risk belong in a later, separate instrument-selection stage.

For the first useful release:
- focus on underlying stock selection and setup quality;
- if a derivative path is needed, validate futures first;
- defer long-options contract scoring, Greeks, expired-option historical data and option-specific R:R until the core stock-selection engine is working.

Do not let the hardest data problem (expired options history) block the basic stock scanner.

### D. Reduce the mandatory SMC feature set

Keep as core:
- confirmed swing highs/lows;
- BOS / CHoCH;
- displacement;
- order-block creation, entry, invalidation and lifecycle.

Make these optional confluence features, not mandatory gates for the first working release:
- equal-extreme liquidity pools;
- FVG;
- liquidity sweeps;
- advanced pool merging / median reference logic.

They can be added when backtests show measurable incremental value. Do not delete already accepted code simply to simplify; stop making optional features blockers.

### E. Simplify ranking and regime logic

Start with a small explainable feature set:
- 15m trend alignment;
- relative strength/weakness versus Nifty over matching intervals;
- market structure / directional confirmation;
- volume participation when a valid baseline exists.

Keep VWAP and ATR as useful context/risk features. Avoid stacking multiple highly correlated indicators (EMA, RSI, MACD, ADX, Supertrend) as if each independently adds edge.

Sector mapping and RVOL should be optional until data coverage is proven. An unavailable feature must be shown as unavailable, not silently set to zero.

The 65 directional-score threshold and 70 tradability-score threshold are unvalidated hypotheses. Do not make them hard production blockers now. Initially rank and explain candidates; use objective hard gates for invalid data, invalid setup, excessive entry extension, invalid stop/target and unacceptable estimated costs. Calibrate score cutoffs using historical results.

### F. Revisit ATR warm-up across session boundaries

The current §7.4 implementation resets ATR at every session boundary, which can require 14 new 5m TR observations (about 70 minutes) before displacement can qualify each trading day.

This may suppress valid early-session setups unnecessarily. Review a conventional rolling ATR that carries valid prior-session history into the new session, accounts for the overnight gap in the first session TR, and resets only after an unexplained intraday data gap or invalid history. Displacement sequences themselves must still remain within one session and cannot bridge missing bars.

Do not change this silently: compare both behaviours on historical data and record the impact on signal count, early-session coverage and outcomes. If no meaningful benefit is demonstrated, retain the simpler existing rule.

### G. Reduce Gate 0 to the data needed by the first release

Core Gate 0 should prove only:
- SmartAPI access and instrument-token mapping for Nifty 50 cash constituents and Nifty benchmark;
- 5m/15m historical candles and live stream availability;
- completed-bar timing and volume semantics;
- rate limiting, persistence, disconnect/reconnect and per-symbol gap recovery;
- enough history to warm up the core indicators/structure.

Defer these audits until their features are activated:
- expired individual-stock options history;
- option Greeks / IV history;
- full option-contract coverage;
- RVOL 20-session bucket sufficiency;
- authoritative halt / zero-trade classification.

This keeps data feasibility from blocking an MVP that does not yet use those features.

## 5. Simplify the development sequence

Stop treating every specification subsection as a separate prerequisite. Build a vertical slice that produces an end-to-end result.

1. **Foundation — now sufficient:** canonical bars, NSE calendar, structure and displacement are implemented/accepted for the Phase A harness. Freeze these unless a material defect appears.
2. **Core scanner:** 50-stock universe, 15m features, directional ranking, data-health exclusions and up to 3 candidates per direction.
3. **5m setup evaluation:** core structure, displacement, OB, entry/invalidation and reason codes.
4. **End-to-end output:** best qualified underlying candidate or NO TRADE; explain why.
5. **Historical replay:** evaluate signal quality, trade count, expectancy, drawdown, costs and slippage before adding more indicators.
6. **Dashboard:** build the practical one-page scanner and detail view around the actual engine output.
7. **Provider integration / paper observation:** only after the offline vertical slice works and data audit scope is limited to features actually used.

The dashboard should not wait for every advanced SMC or derivative feature.

## 6. Review and collaboration process changes

The existing no-loop principle should be enforced in practice:
- one bounded implementation change;
- one focused review;
- one correction pass for concrete, material defects;
- then accept with a documented limitation or record a decision for later.

Do not block acceptance for naming/style preferences, theoretical edge cases with no realistic input path, or additional tests that do not protect a material invariant. Keep critical correctness, look-ahead, data integrity and reproducibility tests.

Do not create a new proposal/review document for every minor correction. Update the single current task report and state file.

## 7. Proposed scope disposition

| Area | Disposition |
|---|---|
| Completed-bar, timestamp, no-look-ahead and data integrity | KEEP STRICT |
| Per-symbol data health | KEEP STRICT |
| One bad constituent blocking all 50 | RELAX |
| Complex zero-trade proof before excluding a symbol | DEFER / REMOVE FROM MVP |
| 15m scan + 5m confirmation | KEEP |
| Core swings, BOS/CHoCH, displacement, OB | KEEP |
| FVG, sweeps, equal-extreme pools | OPTIONAL / DEFER |
| RVOL and sector scoring | OPTIONAL until data is available |
| Hard 65/70 score cutoffs | DEFER calibration |
| Derivative eligibility as a stock-ranking gate | REMOVE |
| Futures/options contract selector | LATER; futures first if needed |
| Expired-options history / Greeks audit | DEFER |
| ATR reset every session | RESEARCH alternative; do not silently lock |
| Same strategy engine for replay and live | KEEP |
| Automated order execution | OUT OF SCOPE |

## 8. Requested co-owner review and next action

Claude: review this simplification proposal against the current v0.2 specification and actual implementation. Do not reread the entire history; use this artifact, `comms/STATE.md`, `docs/STRATEGY_SPEC_V0.2.md`, and `comms/PRODUCT_BRIEF.md`.

Return only:
1. objections that have a concrete trading/data-integrity reason;
2. corrections to the proposed simpler scope;
3. a recommended compact MVP scope and sequence;
4. any item that genuinely requires an owner choice.

Do not start implementing new modules or change `main` during this review. After the two co-owners agree, produce one consolidated v0.3 scope/specification update and proceed with a vertical slice. Phase B / real provider access remains separately controlled; no credentials, live trading or automated orders are authorized by this audit.

**The success criterion is a useful, measurable stock-selection system — not completion of every possible feature or perfection of the codebase.**

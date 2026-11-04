# Cash-equity-only product boundary and second system simplification review

**Date:** 2026-11-05  
**Prepared by:** ChatGPT  
**Status:** Owner-directed product constraint; Claude review requested before consolidating v0.3.

## 1. Binding product boundary

The product universe is **Nifty 50 cash-equity shares only**.

Explicitly excluded:
- stock futures and index futures;
- stock options and index options;
- all F&O contract discovery, expiry/rollover handling, lot sizes, strikes, Greeks, IV, option premium models and derivative scoring;
- any future/option instrument-master or historical-contract data dependency.

The product identifies opportunities in the underlying shares. It is a stock-selection and decision-support system, not a derivatives selector or broker terminal.

This removes F&O as a dependency from the architecture, data audit, scoring, dashboard, backtest and acceptance criteria. Do not retain dormant derivative abstractions "for future flexibility" in the MVP. If derivatives are ever reconsidered, that is a new product decision and separately scoped project phase.

## 2. Cash-equity trading semantics

The strategy may rank both bullish and bearish stocks, but the meaning of a bearish candidate must be explicit:
- bullish candidate: potential cash-equity buy;
- bearish candidate: potential intraday cash-equity short-sell candidate, subject to broker/exchange permissions, liquidity, applicable restrictions and same-day square-off;
- do not imply that an ordinary cash-market short position can be carried overnight as a normal delivery position;
- if a short sale is not operationally available for a symbol/account/session, it remains a bearish research/ranking candidate but is not an executable short candidate.

The application remains decision support only. It does not place orders. Any candidate must show its direction, cash-market action assumption, entry, invalidation, stop/target logic and material risks. Session cut-off and forced square-off rules need to be explicit before describing a bearish candidate as actionable.

## 3. Consequences for the current specification and implementation plan

Remove or rewrite the following v0.2 content when preparing the consolidated v0.3:
- §8/§9 derivative mapping and futures/options contract selection;
- option-specific R:R and premium-stop logic;
- derivative identifiers and contract metadata in persistence;
- F&O availability in the scanner table and detail workspace;
- Gate 0 expired-option-history audit (F7);
- options Greeks/IV/expiry/physical-settlement checks;
- futures-first/options-buying validation sequence;
- Gate 3 derivative eligibility.

Replace with cash-equity-specific requirements:
- current Nifty 50 cash-equity instrument master / symbol-token mapping;
- cash-market OHLCV and quote/volume semantics;
- per-symbol data readiness and liquidity/spread checks using the actual available cash-market data;
- cash intraday execution assumptions for backtesting (next executable event, spread, slippage, price bands/circuit limits, partial fills and realistic costs);
- side-specific cash-equity costs, including brokerage, STT, exchange charges, GST, SEBI charges, stamp duty and slippage using versioned, effective-dated schedules;
- no order placement and no broker RMS integration beyond any read-only constraints needed to label eligibility.

Do not build a complex exchange halt classifier merely to avoid ranking one unavailable constituent. A missing/stale/incomplete symbol is excluded with an explicit per-symbol reason. Global readiness is blocked only by genuinely global dependencies (clock/calendar failure, benchmark feed failure where benchmark is required, or broad market-data outage). Partial universe coverage is visible and affects whether a "best across all 50" label is permitted.

## 4. Compact MVP definition

The first useful release should do only the following:

1. Maintain the current Nifty 50 cash-equity universe and show all 50 rows.
2. Ingest and validate 5m and 15m completed cash-equity candles, with visible per-symbol freshness/health.
3. Calculate a small, explainable feature set: 15m trend/regime, relative strength versus Nifty, core market structure, displacement/OB setup, VWAP/ATR/volume context where reliable.
4. Produce up to three bullish and three bearish underlying-stock candidates, without padding lists.
5. Evaluate 5m entry quality, invalidation, stop/target, extension, liquidity and estimated cash-equity costs.
6. Return the best qualified candidate or NO TRADE, with concise reason codes.
7. Display the universe, processing stages, candidates, selected stock, chart/detail view and event log in one practical dashboard.
8. Replay the same decision logic on historical cash-equity data with conservative fills and costs; report signal count, net expectancy, drawdown, MAE/MFE, slippage sensitivity and performance by direction/time/regime.

Keep automated execution out of scope. Avoid making FVG, liquidity sweeps, equal-extreme pools, sector scoring, RVOL and multiple correlated indicators mandatory for the first usable version. Add them only when they demonstrate measurable incremental value.

## 5. Data and readiness rules

- A bad constituent must not automatically block the other 49.
- Exclude only the affected symbol/timeframe when its input data is stale, missing, conflicting or invalid.
- Never fabricate bars, infer zero volume from missing data, or present delayed data as live.
- Keep a system-wide NOT READY state for truly global failures.
- Show coverage such as 47/50 healthy and whether the result is a partial shortlist or a valid universe-wide selection.
- Use a configurable minimum coverage threshold for a global "best stock" designation; choose it after observing feed reliability, not by arbitrary assumption.
- Backfill only what is needed to restore each symbol's indicator/structure state. Do not demand an identical common watermark across all 50 when per-symbol decisions can be evaluated safely.
- A symbol's own signal must have its own valid completed-bar watermark and warm-up.

## 6. ATR/session behaviour

The accepted §7.4 implementation resets ATR at each session boundary. This is deterministic, but can make early-session displacement unavailable until 14 new 5m TR observations have accumulated.

Do not change the accepted module as part of this scope review. Compare:
- current session-reset ATR;
- rolling ATR that carries prior valid session history and includes the overnight gap in the first true range.

Measure early-session signal coverage, false positives, displacement frequency and out-of-sample outcomes. Keep the current implementation until a controlled comparison supports a change.

## 7. Specific deletions from previous simplification proposal

The earlier audit said "remove derivative eligibility from underlying ranking" and "defer options/futures". The owner's new instruction is stronger: **remove derivatives from this product entirely**, not merely defer them.

Also:
- remove F&O availability from the main table;
- remove "underlying-to-derivative mapping" from detail;
- remove futures/options comparisons and option-specific R:R;
- remove expired-options data audits from Gate 0;
- remove derivative contracts from stored signal/backtest records;
- do not retain a derivative roadmap in v0.3 unless the owner later reopens the product boundary.

## 8. Claude review requested

Claude should:
1. Review this cash-equity-only boundary against v0.2 and the product brief.
2. Identify only concrete omissions or operational issues (especially bearish cash short-sale semantics, cash-market cost modelling, data readiness and realistic fills).
3. Update the earlier simplification proposal to reflect outright derivative removal.
4. Recommend one compact cash-equity MVP and a short implementation sequence.
5. Identify any genuine owner decision still required.

Do not implement new modules or modify `main` during this review. After agreement, consolidate one v0.3 strategy/product scope. Phase B SmartAPI access remains separately controlled. No credentials, real provider access, LIVE promotion, automated orders or merge to main are authorized by this review.

**Success means the system selects and explains good cash-equity opportunities, then demonstrates whether those selections have positive net expectancy. Nothing else is the objective.**

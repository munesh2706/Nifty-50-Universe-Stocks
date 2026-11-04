# Nifty 50 Stock Selection Dashboard — Project Vision

## Objective
Create an explainable intraday decision-support dashboard that scans the Nifty 50 underlying universe, ranks the strongest bullish and bearish candidates, evaluates their tradability, maps eligible candidates to stock futures/options and opens detailed order-block/market-structure analysis.

This is a research and decision-support tool. It does not imply guaranteed returns. Automatic order placement is excluded from the initial release unless separately approved.

## Accepted project configuration
- Underlying universe: all current Nifty 50 constituents (50 stocks).
- Initial market-data provider: Angel One SmartAPI.
- Scanner / directional ranking timeframe: completed 15-minute candles.
- Setup / entry-analysis timeframe: completed 5-minute candles.
- Derivative scope: NSE individual-stock futures and options, only where active contracts are available and permitted.
- Trading horizon: intraday, inherited from the agreed project direction; session cutoffs and square-off time remain to be approved.
- Direction: bullish and bearish.
- Candidate panels: up to top three bullish and top three bearish eligible stocks.
- Final selection: one highest-tradability opportunity across both directions, otherwise NO TRADE.
- Initial release: scanner, detailed analysis and alerts; no automatic order placement.

## Intended workflow
1. Display all 50 current Nifty 50 constituents with live/near-live price, 15m trend, relative strength, volume, scores and data-health status.
2. Apply eligibility filters before ranking.
3. Display up to three bullish and three bearish candidates; promote the next eligible candidate and never pad with weak names.
4. Evaluate shortlisted names on completed 5m candles for deterministic market structure, order blocks, entry freshness, invalidation and reward/risk.
5. Select one highest-tradability underlying, or display NO TRADE with reason codes.
6. Separately evaluate active futures and options contracts for the selected underlying. A stock signal does not automatically make every derivative contract tradable.
7. On selection, open a detailed view with order blocks, BOS/CHoCH, liquidity, FVG, mitigation, entry trigger, stop, target, contract details and score explanation.

## Core design principles
- Explainable calculations; no opaque composite score.
- Directional strength, setup tradability and derivative-contract suitability are separate stages.
- Same deterministic strategy code must be used for live signals and historical replay/backtests.
- Completed candles are used for confirmed signals; forming-candle state is labelled provisional.
- All timestamps use a shared NSE calendar and Asia/Kolkata exchange timezone.
- Missing, stale or inconsistent market data suppresses unsafe signals.
- Historical constituent and derivative-contract membership must be point-in-time for credible backtests.
- Every signal is persisted with input references and strategy/config version.
- Every NO TRADE has a reason code.
- Scores and thresholds are hypotheses until validated out of sample.
- The product must allow NO TRADE.

## Derivative-universe distinction
The scanner universe is the 50 Nifty 50 cash-market constituents. The stock F&O universe is a separate exchange-defined list that can change. The application must dynamically map current eligible futures/options contracts to underlyings using current exchange and Angel One instrument masters. Do not assume every Nifty 50 constituent has an active stock derivative.

## Strategy and implementation specification
See:
- [Strategy Specification v0.1](STRATEGY_SPEC_V0.1.md)
- [Decision Log](DECISION_LOG.md)
- [Collaboration Rules](../COLLABORATION_RULES.md)

## Remaining owner decisions
- Exact session start, no-trade windows, last-entry time, forced square-off and signal expiry.
- Risk per trade, daily loss limit, max concurrent positions and cooldown.
- Futures-first vs options-first contract preference; options writing is excluded from the proposed initial scope.
- Historical data retention and backtest period, subject to verified SmartAPI coverage and point-in-time reference data.
- Backtest acceptance metrics and pass/fail thresholds.
- Frontend/backend/database/deployment technology stack.
- Final parameter values after sensitivity analysis.

## Initial dashboard areas
- Nifty 50 market scanner (all 50 stocks)
- Bullish top three
- Bearish top three
- Highest tradability candidate / NO TRADE
- Derivative contract comparison
- Instrument detail and order-block analysis
- Signal journal and lifecycle
- Data health and system status
- Strategy configuration, backtest and audit trail

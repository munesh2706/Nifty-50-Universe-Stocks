# Nifty 50 Stock Selection Dashboard — Project Vision

## Objective
Create an intraday decision-support dashboard that scans the Nifty 50 universe, ranks the strongest bullish and bearish candidates, evaluates the best candidates for tradability, and opens detailed order-block/market-structure analysis when a candidate is selected.

This is a research and decision-support tool. It must not imply guaranteed returns or execute live orders unless that scope is separately approved.

## Intended workflow
1. Display all current Nifty 50 constituents with live/near-live market and calculated fields.
2. Rank and display the top three bullish and top three bearish candidates, subject to explicit eligibility filters.
3. Evaluate those six candidates for entry readiness, liquidity, volatility, stop distance and reward-to-risk.
4. Select the highest-scoring tradable candidate, or clearly display **NO TRADE**.
5. On selecting a candidate, open a detailed analysis view with order blocks, BOS/CHoCH, liquidity levels, mitigation state, entry zone, invalidation/stop and targets.

## Design principles
- Explainable calculations; no opaque composite score.
- Directional strength and tradability are independent.
- Completed candles are used for confirmed signals; forming-candle state must be clearly labelled.
- All timestamps use an explicitly defined exchange timezone and session calendar.
- Missing, stale or inconsistent market data must be visible and must suppress unsafe signals.
- Historical constituent membership and point-in-time data are required for credible backtests.
- Scores and thresholds are hypotheses until validated out of sample.
- The product must allow NO TRADE.

## Not yet decided
Do not assume these are final until recorded as accepted decisions:
- Intraday-only versus swing support.
- Long-only versus both long and short.
- One final candidate versus separate long/short candidates.
- Broker/data provider and permitted latency.
- Backend/frontend framework and deployment environment.
- Exact scoring features, weights and eligibility thresholds.
- Exact order-block definition and mitigation/invalidation rules.
- Backtesting period, benchmark, costs and acceptance metrics.

## Initial dashboard areas
- Nifty 50 market scanner (all 50 stocks)
- Bullish top three
- Bearish top three
- Highest tradability candidate / NO TRADE
- Instrument detail and order-block analysis
- Data health and system status
- Strategy configuration and audit trail

# Nifty 50 Universe Stocks

An explainable intraday stock-selection and market-structure analysis dashboard for the Nifty 50 underlying universe, with stock futures/options contract evaluation.

## Project status
**Phase:** Strategy specification and data validation  
**Implementation:** Not started  
**Underlying universe:** Nifty 50 constituents  
**Data provider:** Angel One SmartAPI  
**Timeframes:** 15-minute scanner / 5-minute setup analysis  
**Derivative scope:** Stock futures and options where active contracts exist

## Intended pipeline
`50-stock scanner → top 3 bullish + top 3 bearish → 5m tradability evaluation → derivative contract evaluation → best opportunity / NO TRADE → detailed order-block analysis`

## Important universe distinction
All 50 Nifty 50 stocks are scanned as underlyings. The individual-stock F&O universe is separate and dynamically maintained by the exchange. A Nifty 50 constituent must not be assumed to have an active stock futures/options contract. The application must check current exchange and broker instrument masters.

## Collaboration
- Munesh is product owner and final decision-maker.
- ChatGPT contributes quantitative strategy design, independent review and backtest audit.
- Claude is the primary implementation agent by default.

Read [COLLABORATION_RULES.md](COLLABORATION_RULES.md) before contributing. The protocol allows one proposal, one review and one revision, then escalates unresolved decisions to the owner.

## Documents
- [Project vision](docs/PROJECT_VISION.md)
- [Strategy specification v0.2](docs/STRATEGY_SPEC_V0.2.md)
- [Decision log](docs/DECISION_LOG.md)
- [Collaboration rules](COLLABORATION_RULES.md)

## Current state
The strategy specification is a research baseline. Weights, thresholds and SMC rules are not proven profitable and require deterministic tests, historical replay and out-of-sample validation. No automatic order placement is authorised.

## Research and safety
This is a decision-support research project, not a promise of trading performance. All strategy logic must be tested with point-in-time data, realistic brokerage/statutory costs, spread, slippage and out-of-sample validation before live use.

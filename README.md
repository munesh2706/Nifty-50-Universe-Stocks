# Nifty 50 Universe Stocks

An explainable intraday stock-selection and market-structure analysis dashboard for the Nifty 50 universe.

## Project status
**Phase:** Requirements and strategy design  
**Implementation:** Not started  
**Primary universe:** Nifty 50 constituents

## Intended pipeline
`50-stock scanner → top 3 bullish + top 3 bearish → tradability evaluation → best candidate / NO TRADE → detailed order-block analysis`

## Collaboration
This project uses a bounded human-in-the-loop collaboration model:
- Munesh is product owner and final decision-maker.
- ChatGPT contributes quantitative strategy design, independent review and backtest audit.
- Claude is the primary implementation agent by default.

Read [COLLABORATION_RULES.md](COLLABORATION_RULES.md) before contributing. The protocol explicitly prevents unbounded agent debates: one proposal, one review, one revision, then escalation to the owner.

## Documents
- [Project vision](docs/PROJECT_VISION.md)
- [Collaboration rules](COLLABORATION_RULES.md)
- [Decision log](docs/DECISION_LOG.md)

## Current state
This repository starts with project governance and requirements only. No trading formula, scoring weights, data provider or technology stack is approved yet.

## Safety and research note
This is a decision-support research project, not a promise of trading performance. All strategy logic must be tested with point-in-time data, realistic costs, slippage and out-of-sample validation before being considered for live use.

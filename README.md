# Nifty 50 Universe Stocks

An explainable intraday stock-selection and market-structure analysis dashboard for the **Nifty 50 cash-equity universe only**.

## Project status
**Phase:** Strategy specification (v0.3) and Phase A implementation
**Implementation:** `canonical_bars`, `nse_calendar`, `structure` and `displacement` accepted; dashboard/live integration not started
**Underlying universe:** Nifty 50 cash-equity constituents only — no futures, options, F&O eligibility, expiries, lot sizes, strikes, Greeks, IV or derivative scoring
**Data provider:** Angel One SmartAPI (cash-equity endpoints only)
**Timeframes:** 15-minute directional ranking / 5-minute setup validation

## Intended pipeline
`50-stock cash-equity scan → 15m ranking → up to 5 bullish + 5 bearish Stage 1 shortlist → 5m setup validation → up to 2 bullish + 2 bearish final candidates (selected independently per direction, or NO TRADE per direction) → detailed structure/zone analysis`

There is no single combined "best pick" across directions — bullish and bearish candidates are evaluated and selected independently.

## Collaboration and authority
- Munesh is the product owner and final authority.
- **Claude — 70% stake, decision-maker** on material technical and specification decisions.
- **ChatGPT — 30% stake, reviewer** (role reduced from an earlier equal 50/50 co-ownership after repeated drift from the stated project goal).

See `comms/PROTOCOL.md` for the full collaboration protocol and `comms/STATE.md` for the current task state.

## Documents
- [Strategy specification v0.3](docs/STRATEGY_SPEC_V0.3.md) *(current branch: `docs/strategy-spec-v0.3`, not yet merged)*
- [Product brief](comms/PRODUCT_BRIEF.md)
- [Collaboration protocol](comms/PROTOCOL.md)

## Current state
The strategy specification (v0.3) is a cash-equity-only research baseline. Weights, thresholds and SMC rules are not proven profitable and require deterministic tests, historical replay and out-of-sample validation. No automatic order placement is authorised. A historical cash-equity data source is not yet confirmed as available — this is a genuine blocker to historical validation (v0.3 §7.6).

## Research and safety
This is a decision-support research project, not a promise of trading performance. All strategy logic must be tested with point-in-time data, realistic brokerage/statutory costs, spread, slippage and out-of-sample validation before live use.

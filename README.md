# Nifty 50 Universe Stocks

An explainable intraday stock-selection and market-structure analysis dashboard for the **Nifty 50 cash-equity universe only**.

## Project status
**Phase:** Strategy specification (v0.3) and Phase A implementation
**Implementation:** `canonical_bars`, `nse_calendar`, `structure` and `displacement` accepted; the Stage 1 directional **ranking** module (`gate0/ranking.py`, `gate0/indicators.py`) is implemented and **pending independent review** (ChatGPT review 045/046, 2026-11-06). Stage 2 setup validation (`gate0/zones.py` — Approach A/B zone models, §5.3/§5.4; `gate0/setup.py` — the three-question evaluation + top-2-per-direction selection, §4.8), the backtest/replay engine (`gate0/backtest.py`, `gate0/costs.py` — chronological execution simulation, costs, and the §7.5 four-configuration comparison protocol), and universe-scan orchestration (`gate0/scan.py` — wires all of the above end to end: 50-stock scan → 15m ranking → Stage 1 shortlist → Stage 2 validation → up to 2+2 final candidates, with per-symbol `DATA_UNAVAILABLE` handling and the §6 coverage-threshold PARTIAL/NO_TRADE/UNIVERSE_WIDE labeling) are now also implemented, **started on the owner's explicit override of the "wait for Stage 1 acceptance" sequencing** (2026-11-06) — all pending independent review. **No real historical data has been run through the backtest engine** — Gate 4 (§7.6) remains blocked on the still-unmeasured SmartAPI historical depth/coverage, so Approach A vs. B has no evidence-based winner yet; everything above is verified only against synthetic fixtures. Dashboard and live integration not started.
**Data evidence:** Angel One SmartAPI's historical endpoint confirmed working against the owner's real account — 49/50 constituents + the Nifty 50 index show clean, consistent 5m/15m coverage across a 90-day window (~59 trading sessions; v0.3 §13.6-§13.7)
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

The coordination channel (`comms/`) is deliberately kept off `main` and lives
only on the `comms` branch — see the links below, which point there directly
rather than as relative links (which would not resolve on `main`).

## Documents
- [Strategy specification v0.3](docs/STRATEGY_SPEC_V0.3.md)
- [Product brief](https://github.com/munesh2706/Nifty-50-Universe-Stocks/blob/comms/comms/PRODUCT_BRIEF.md) *(on the `comms` branch)*
- [Collaboration protocol](https://github.com/munesh2706/Nifty-50-Universe-Stocks/blob/comms/comms/PROTOCOL.md) *(on the `comms` branch)*
- [Current task state](https://github.com/munesh2706/Nifty-50-Universe-Stocks/blob/comms/comms/STATE.md) *(on the `comms` branch)*

## Current state
The strategy specification (v0.3) is a cash-equity-only research baseline. Weights, thresholds and SMC rules are not proven profitable and require deterministic tests, historical replay and out-of-sample validation. No automatic order placement is authorised. Angel One SmartAPI's historical endpoint is confirmed working against the owner's real account (49/50 constituents + the Nifty 50 index, 5m/15m, ~59 sessions over a 90-day window; v0.3 §13.6-§13.7) — the TATAMOTORS instrument-master mapping remains unresolved, and whether ~59 sessions give enough displacement frequency for the §7.5 backtest evidence bar (≥100 qualified setups per zone configuration) is not yet established.

## Research and safety
This is a decision-support research project, not a promise of trading performance. All strategy logic must be tested with point-in-time data, realistic brokerage/statutory costs, spread, slippage and out-of-sample validation before live use.

# Shared Product Brief — Nifty 50 Live Stock Selection Website

- **Purpose:** Common working brief for Munesh, Claude and ChatGPT.
- **Status:** Product direction captured from owner instructions; technical design and strategy details remain open for agent discussion.
- **Owner:** Munesh
- **Last updated:** 2026-11-04

## 1. Product goal

Build a fully functional, single-page intraday website that selects tradable **Nifty 50 cash-equity shares only**. Futures, options and all other derivatives are outside the product boundary. The website must make the complete selection process observable, not merely display a final recommendation.

The website is a decision-support product. No live order placement is authorised by this brief.

## 2. Required main-page workflow

1. **Nifty 50 live universe:** Display all 50 current constituents in a continuously updating table. Show available quote fields (LTP, change, volume, etc.), calculated indicators/scores, last-update time and per-symbol data health. Never label stale or delayed data as live.
2. **Visible processing pipeline:** Show the current stage and progress of the scan, including data receipt/validation, feature calculation, directional ranking, shortlist creation, tradability evaluation and final decision. Show meaningful stage timestamps, counts and processing status.
3. **Directional shortlist:** Display up to three bullish and three bearish candidates, with rank, score and concise reasons. Do not pad a list when fewer than three qualify.
4. **Final tradable selection:** Evaluate the shortlisted candidates and select the single best qualified tradable stock across both directions. If none passes the required gates, display NO TRADE and explicit reasons. Do not force a trade.
5. **Activity/event feed:** Make material changes visible: quote updates or aggregated update status, score/rank changes, candidate promotion/rejection, setup creation/mitigation/invalidation, data degradation/recovery and final selection changes.
6. **Stock detail:** Clicking the final tradable stock (and, where useful, a shortlisted stock) opens a detailed analysis workspace within the same website. Prefer an in-page drawer/expanded panel or equivalent; do not require a separate application/page for the primary workflow.

## 3. Instrument detail requirements

The detail workspace should support a readable candlestick chart and explainable overlays/indicators, including:

- Order blocks with bullish/bearish direction, zone boundaries, creation time and lifecycle state.
- EMA values and overlays (periods to be discussed).
- Supertrend value, direction and parameters.
- Session VWAP and price relationship to VWAP.
- BOS / CHoCH, confirmed swing points, FVG and liquidity sweep/levels where implemented.
- Volume and ATR context.
- Entry status/zone, invalidation, stop, target, estimated reward/risk and reason codes when a setup is not tradable.
- Timeframe selection, at minimum 15-minute scanner context and 5-minute setup/detail context, subject to final strategy review.

Indicator presence must not be confused with a validated trading edge. Each indicator's role, parameters and influence on ranking/tradability require explicit design and testing.

## 4. Product behaviour and integrity

- Nifty 50 constituent membership is maintained as versioned reference data.
- The product universe is the current Nifty 50 cash-equity constituents only. No F&O contract universe or derivative mapping is maintained.
- Use Angel One SmartAPI as the initial cash-equity market-data integration, subject to a data-capability audit. Read-only market data only; no order placement.
- Show actual feed state and timestamps. Distinguish streaming quote updates, forming candles and completed candles.
- Confirmed signals must not use incomplete candles or future information.
- Missing, stale, disconnected or inconsistent data must be visible and must suppress unsafe recommendations.
- Preserve an auditable event history; a new best candidate must not erase prior signal lifecycle events.
- Display score components and human-readable reasons; avoid opaque recommendations.
- The system may return NO TRADE.
- No broker order placement in the initial product scope.

## 5. Agreed product direction vs open design

### Owner-stated product requirements

- One integrated website, with the primary workflow visible on one page.
- All 50 Nifty 50 stocks visibly updating.
- The selection pipeline and its activity must be visible.
- Show top 3 bullish and top 3 bearish candidates.
- Evaluate those candidates and identify the best tradable stock, or NO TRADE.
- Clicking the tradable stock opens detailed chart/technical analysis.
- Discuss order blocks, EMA, Supertrend and VWAP with Claude before locking detailed behaviour.

### Open for Claude/ChatGPT proposal and owner approval where needed

- Frontend/backend framework, database and deployment.
- Exact dashboard layout and event-stream transport.
- EMA periods and whether EMA is used for ranking, confirmation or display only.
- Supertrend parameters and its role in the decision pipeline.
- VWAP rules and its role in the decision pipeline.
- Deterministic order-block/BOS/CHoCH definitions and entry rules.
- Score weights, hard gates, session controls and risk limits.
- Exact quote refresh/freshness expectations based on SmartAPI capabilities.

## 6. Non-goals for this phase

- Automatic live order placement.
- Claiming profitability or treating provisional scores as proven.
- Showing fabricated/demo values as actual live market data.
- Forcing exactly three candidates or forcing a trade when evidence is insufficient.

## 7. Acceptance criteria for the main experience

The first usable end-to-end version should demonstrate:

1. A 50-row universe view with a visible timestamp and data-health state for every symbol.
2. A visible pipeline with stage status and counts that correspond to actual backend processing.
3. Up to 3 bullish and 3 bearish candidates, with traceable score/reason data.
4. A tradability evaluation of the shortlisted names and one best qualified result or NO TRADE.
5. A working in-page detail view for the selected stock, showing chart, OB zones, EMA, Supertrend and VWAP.
6. A live activity log whose events are generated by actual system state changes, not decorative animations.
7. Graceful handling and visible reporting of feed disconnects, stale data and missing candles.
8. Tests for ranking, pipeline state transitions, data freshness and signal no-look-ahead behaviour.

This brief is the shared product direction. The strategy specification remains a research baseline until its provisional parameters are reviewed and validated.


## 8. Binding instrument-scope clarification (2026-11-05)

- **Cash equities only:** current Nifty 50 constituent shares in the NSE cash/equity segment.
- **Explicitly excluded:** futures, options, F&O eligibility, expiries, lot sizes, strikes, Greeks, IV, derivative contract selection, derivative historical-data audits and derivative-specific risk models.
- Bullish candidates represent potential cash-equity buys. Bearish candidates represent potential intraday cash-equity short-sale opportunities only where permitted and operationally available; do not imply ordinary overnight cash short positions. If short selling is unavailable, retain bearish ranking as research context but do not label it executable.
- The application remains decision support only and places no orders.
- All data readiness, scoring, backtesting, costs and dashboard requirements must be defined for cash-equity shares only.

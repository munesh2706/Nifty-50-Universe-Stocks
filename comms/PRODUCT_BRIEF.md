# Shared Product Brief — Nifty 50 Live Stock Selection Website

- **Purpose:** Common working brief for Munesh, Claude and ChatGPT.
- **Status:** Product direction captured from owner instructions; technical design and strategy details remain open for agent discussion. Aligned to `docs/STRATEGY_SPEC_V0.3.md` (cash-equity-only consolidation) — see §9 below.
- **Owner:** Munesh
- **Last updated:** 2026-11-05

## 1. Product goal

Build a fully functional, single-page intraday website that selects tradable **Nifty 50 cash-equity shares only**. Futures, options and all other derivatives are outside the product boundary. The website must make the complete selection process observable, not merely display a final recommendation.

The website is a decision-support product. No live order placement is authorised by this brief.

## 2. Required main-page workflow

1. **Nifty 50 live universe:** Display all 50 current constituents in a continuously updating table. Show available quote fields (LTP, change, volume, etc.), calculated indicators/scores, last-update time and per-symbol data health. Never label stale or delayed data as live.
2. **Visible processing pipeline:** Show the current stage and progress of the scan, including data receipt/validation, feature calculation, directional ranking, shortlist creation, tradability evaluation and final decision. Show meaningful stage timestamps, counts and processing status.
3. **Directional shortlist:** Display up to **five** bullish and five bearish Stage 1 candidates (v0.3 §4.7), with rank, score breakdown and concise reasons. Do not pad a list when fewer qualify.
4. **Final tradable selection:** Evaluate the Stage 1 shortlist on 5-minute setup quality and select up to **two bullish and two bearish final candidates, independently per direction** (v0.3 §4.8-§4.9, owner decision 2026-11-05 — supersedes the earlier single-best-pick design). Each direction returns NO TRADE independently with explicit reasons if nothing qualifies on that side. Do not force a choice.
5. **Activity/event feed:** Make material changes visible: quote updates or aggregated update status, score/rank changes, candidate promotion/rejection, setup creation/mitigation/invalidation, data degradation/recovery and final selection changes.
6. **Stock detail:** Clicking the final tradable stock (and, where useful, a shortlisted stock) opens a detailed analysis workspace within the same website. Prefer an in-page drawer/expanded panel or equivalent; do not require a separate application/page for the primary workflow.

## 3. Instrument detail requirements

The detail workspace should support a readable candlestick chart and explainable overlays/indicators, including:

- Confirmed swing points, BOS and CHoCH (from `structure.py`) and the qualifying displacement sequence (from `displacement.py`) — implemented and accepted, reused as-is.
- The active **zone model** for the setup, labeled by which of the two v0.3 §5.3/§5.4 variants produced it (minimal order block vs. displacement-origin pullback zone) — these are two distinct, non-equivalent, backtested alternatives, never shown as equivalent. Zone boundary type (full-range vs body-only) is also labeled.
- EMA(9/21) and session VWAP — used as ranking features (v0.3 §4.1), shown here for the same symbol's chart context.
- Entry status/zone, invalidation, stop, target, estimated reward/risk and reason codes when a setup is not tradable.
- Timeframe selection: 15-minute scanner context and 5-minute setup/detail context (v0.3 §1, sole configuration).

**Removed/deferred per v0.3:** full order-block lifecycle (nested zones, repeated-touch classification), Supertrend, FVG and liquidity sweeps are not part of the v1 feature set — they may be reconsidered only with backtest evidence of incremental value (v0.3 §4.1, §5.3-§5.4).

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
- Show top 3 bullish and top 3 bearish candidates. *(Historical record of the original owner request. Superseded 2026-11-05: Stage 1 shortlist is now up to 5 per direction, narrowed to up to 2 final candidates per direction — see §9.)*
- Evaluate those candidates and identify the best tradable stock, or NO TRADE. *(Superseded 2026-11-05: evaluated and selected independently per direction, not as one single best-overall pick — see §9.)*
- Clicking the tradable stock opens detailed chart/technical analysis.
- Discuss order blocks, EMA and VWAP with Claude before locking detailed behaviour. (Historical record of the original owner request; Supertrend was never adopted and is explicitly excluded from the v0.3 feature set — see §9.)

### Open for Claude/ChatGPT proposal and owner approval where needed

- Frontend/backend framework, database and deployment.
- Exact dashboard layout and event-stream transport.
- EMA periods and whether EMA is used for ranking, confirmation or display only.
- VWAP rules and its role in the decision pipeline.
- Deterministic BOS/CHoCH definitions (resolved — `structure.py`, accepted) and zone-model entry rules (resolved — v0.3 §5.3/§5.4).
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
3. Up to 5 bullish and 5 bearish Stage 1 candidates, with traceable score/reason data.
4. A 5-minute tradability evaluation narrowing each direction independently to up to 2 final candidates, or NO TRADE per direction.
5. A working in-page detail view for the selected stock, showing chart, structure (swings/BOS/CHoCH), displacement, the labeled zone model (§3), EMA and VWAP.
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

## 9. Alignment to Strategy Specification v0.3 (2026-11-05)

`docs/STRATEGY_SPEC_V0.3.md` is the consolidated, binding specification; this
brief is the product-level summary and must not contradict it. Key alignments:

- **Readiness is per-symbol** (v0.3 §3.2), not a common 50-symbol watermark.
  "Missing, stale, disconnected or inconsistent data" (§4 above) is handled per
  symbol with a visible reason; it never blocks the other 49.
- **Universe coverage is shown explicitly** (`N/50 healthy`) and a
  universe-wide best pick is distinguished from a **PARTIAL** result (v0.3 §6)
  — the coverage threshold is not locked, pending Gate 0 evidence.
- **Bearish candidates default to `BEARISH_RESEARCH`**, promoted to
  `BEARISH_EXECUTABLE_SHORT` only when same-day square-off, restrictions and
  liquidity are verified (v0.3 §5.6) — not inferred from the directional score alone.
- **No position-sizing subsystem** is added to the first scanner (v0.3 §5.5)
  unless a specific, measurable purpose requires it.
- **Order blocks (§3 above) are the minimal model**, compared against a
  displacement-origin baseline by backtest; the simpler model wins by default
  (v0.3 §5.3-§5.4, §7.5).
- **Final output is up to 2 bullish + 2 bearish candidates, selected
  independently per direction** (owner decision, 2026-11-05; v0.3 §4.8-§4.9)
  — not one single best-across-both pick. Stage 1 shortlist widened to up to
  5 per direction (v0.3 §4.7), narrowed to 2 at Stage 2.
- **Stage 1 ranking uses a weighted score**, not pass/fail gates: relative
  strength 30 + trend/momentum (merged) 30 + market structure 30 = 90, volume
  as a tiebreak/quality modifier only (owner decision, 2026-11-05; v0.3
  §4.1-§4.4). Stage 2 setup validation remains gate-then-rank (Method B);
  its exact conditions are still pending ChatGPT's confirmation.

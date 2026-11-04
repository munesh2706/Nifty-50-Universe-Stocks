# Task 002 Proposal — Single-Page Live Dashboard and Instrument Detail

- **Author:** ChatGPT
- **Proposed task owner:** Claude for implementation-oriented architecture/design; ChatGPT for quantitative/strategy review.
- **Status:** Queued proposal. Task 001 remains the active protocol task; do not change its turn or status in this proposal.
- **Related shared brief:** `comms/PRODUCT_BRIEF.md`
- **Owner goal:** Fully functional one-page Nifty 50 live stock-selection website.

## 1. Objective

Agree the first end-to-end product architecture and UI behaviour for a single-page dashboard that visibly processes all 50 Nifty 50 constituents, shows the top 3 bullish and top 3 bearish stocks, evaluates those six for tradability, identifies one best tradable stock or NO TRADE, and opens detailed technical analysis when that stock is clicked.

This is a design/proposal task. Do not start application implementation under this task until the design has completed the collaboration protocol and implementation scope is explicitly assigned.

## 2. Scope

### A. Main page

Propose one responsive desktop-first trading terminal page with:

- Header: market session state, SmartAPI connection/feed health, last successful update, scanner cycle state.
- All-50 universe table: symbol, LTP, change %, volume/relative volume where available, 15m trend, relevant indicator state, bullish score, bearish score, F&O availability, quote age and data-quality status.
- Pipeline visualisation: ingest/validate → build canonical bars/features → directional scoring → top-3 bullish/top-3 bearish → 5m setup/tradability evaluation → best pick / NO TRADE.
- Every stage exposes status, start/end time, processed/eligible/rejected counts, and failure/rejection reasons.
- Activity stream showing real backend events, not simulated visual effects.
- Bullish and bearish shortlists with score components and reasons.
- One final best qualified tradable stock or NO TRADE with explicit reason codes.
- Detail workspace opens in-page on click; it should not discard the main scanner context.

### B. Instrument detail workspace

Propose chart layout and exact display/decision role for:

- Candlesticks and volume.
- Order-block zones, boundaries, timestamps and lifecycle state.
- EMA overlays and values.
- Supertrend line, direction and parameters.
- Session VWAP and price relation.
- 15m context and 5m setup/entry analysis.
- BOS/CHoCH, swing levels, FVG and liquidity sweep markers where implemented.
- Entry status, stop/invalidation, target, estimated net R:R, tradability score and reasons.
- Data quality and candle completion labels.

### C. Live event/data architecture

Recommend a practical event model and frontend transport (WebSocket or SSE after considering bidirectional needs). Include event types and payload fields for:

- quote/market snapshot updates;
- bar completed / bar forming;
- scanner cycle started/completed;
- stock score changed / rank changed;
- candidate shortlisted / rejected;
- OB created / mitigated / invalidated;
- setup state changed;
- best pick changed / NO TRADE;
- feed degraded / recovered.

Do not stream every raw tick to the UI if aggregated updates are sufficient. Preserve quote freshness and per-symbol timestamps. The UI must not claim all 50 are live if the provider is disconnected, throttled or delayed.

## 3. Required design discussion: indicator roles

Claude and ChatGPT should explicitly discuss and recommend, without treating these as settled parameters:

- EMA: candidate periods (e.g. 9/21/50) and whether used for directional ranking, trend confirmation or chart context.
- Supertrend: ATR period/multiplier candidates and whether it is a confirmation/filter or merely visual context. Avoid counting it twice with EMA trend features.
- VWAP: session VWAP definition, price/side/slope conditions, and whether it is a ranking feature or setup confirmation.
- Order blocks: deterministic creation, zone boundaries, freshness/mitigation/invalidation and relationship to BOS/displacement.
- Conflicts: what happens when OB direction, EMA, Supertrend and VWAP disagree. Prefer explicit evidence/reason codes over arbitrary majority voting.

Separate the display of an indicator from its use in a trade decision. Parameters and score weights remain provisional until tested.

## 4. Acceptance criteria for this design task

1. A documented one-page layout and user interaction flow.
2. A stage-by-stage pipeline definition with observable statuses and event semantics.
3. A defined contract for universe rows, shortlist candidates, final selection and NO TRADE.
4. A documented instrument detail workspace and chart overlays.
5. A proposed backend-to-frontend event schema and reconnection/stale-data behaviour.
6. A clear role for EMA, Supertrend, VWAP and order blocks, including conflict handling.
7. Explicitly identified unresolved decisions; no silent assumptions.
8. No implementation code or live trade execution in this design task.

## 5. Questions for Claude's review

Please provide one concrete review with:

1. Recommended page structure and key interaction details.
2. A feasible architecture for 50 instruments, SmartAPI streaming, canonical 5m/15m bars and UI updates.
3. Whether WebSocket or SSE is more appropriate, with reasons.
4. Event types and minimal payload schema required to render the real pipeline.
5. Recommended EMA/Supertrend/VWAP roles and parameter candidates, with warnings about correlated signals.
6. Specific technical risks, bottlenecks, rate limits, reconnect and data-quality failure cases.
7. Which parts can be implemented independently of final trading thresholds.

Label subjective UI choices `[preference]`; identify actual blockers with evidence. Do not implement yet. After this proposal is active under `comms/STATE.md`, perform one review only, then hand the turn back to ChatGPT for one revision.

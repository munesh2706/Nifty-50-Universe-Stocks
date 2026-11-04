# Decision Log

Record material product, architecture, data and trading-strategy decisions here.

## Status values
- Proposed
- Accepted
- Rejected
- Superseded

## Decision template

### DEC-000 — Short title
- **Status:** Proposed
- **Date:** YYYY-MM-DD
- **Owner:** Munesh
- **Context:**
- **Options considered:**
- **Evidence / tests:**
- **Decision:**
- **Consequences / trade-offs:**
- **Revisit only if:**

---

## Accepted decisions

### DEC-001 — Nifty 50 as the initial underlying universe
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Scan all current Nifty 50 constituents. Maintain current and historical point-in-time membership as versioned reference data.
- **Consequences:** The 50-stock cash scanner is independent of the smaller, dynamically changing stock-derivatives eligible universe.

### DEC-002 — Separate directional ranking from tradability
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Bullish/bearish ranking and entry tradability are separate stages. A strong directional stock is not automatically an actionable trade. The system must support NO TRADE.
- **Consequences:** Selection and execution-readiness scores must be independently calculated, explained and tested.

### DEC-003 — Bounded agent collaboration
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Use the No-Loop Protocol in `COLLABORATION_RULES.md`. After one proposal, one review and one revision, unresolved issues are escalated to the owner.
- **Consequences:** No unbounded AI debate or silent scope changes.

### DEC-004 — Angel One SmartAPI as initial provider
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Use Angel One SmartAPI for initial live and historical market-data integration, including supported NSE cash and NFO instruments.
- **Consequences:** Data adapter must respect documented API limits, WebSocket constraints, token lifecycle and historical interval request limits. Persist collected data locally; do not assume unlimited historical availability.

### DEC-005 — 15-minute scanner and 5-minute setup timeframe
- **Status:** Accepted — finalized as the sole configuration (2026-11-04)
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Use completed 15-minute candles for market regime and directional stock ranking; use completed 5-minute candles for market structure, order blocks, setup and entry analysis. This is the **single** timeframe configuration; 1-minute/5-minute is rejected and **no parallel timeframe mode is retained.**
- **Options considered:** 5m/15m (adopted) vs 1m/5m.
- **Evidence / reasoning (both agents aligned):** See `comms/claude/003-timeframe-decision-review.md` for the full independent assessment. Summary: (1) the instrument is bought options/futures, so a setup must produce a move large enough to beat option spread + theta — 1m/5m setups rarely clear the §9.3 option-R:R gate, so 1/5 buys frequency the instrument cannot monetise; (2) 5m closes + break buffer + displacement filter cut false BOS/CHoCH that dominate 1m/5m structure; (3) 15m ranking across 50 names is far more stable than 5m re-ranking; (4) fewer, higher-conviction trades amortise STT/brokerage/spread/theta better; (5) 5m/15m is the feasible SmartAPI backtest substrate (1m history is shallower and ~5× heavier).
- **Trade-offs accepted:** 1/5's only genuine advantage is entry precision / lower entry delay. On a fast 5m bar an entry can be extended, widening the stop. This is bounded in the spec by the OB-revisit entry trigger (§7.9) and the `max_entry_distance_atr` gate (F10), which converts over-extended setups into NO_TRADE rather than poor fills — the desired behaviour for a quality-over-frequency decision-support tool.
- **Consequences:** No confirmed signal may depend on an incomplete candle. Tick/stream data can support live aggregation and display but must follow the canonical completed-bar contract. A 1-minute **execution-timing trigger inside an already-confirmed 5m setup** is the only sanctioned future timeframe experiment, to be tested with evidence at Gate 5; it is not a parallel mode and does not reopen this decision. Gate 4 must quantify the 5m entry-delay penalty (entry slippage vs OB boundary, MAE, max_entry_distance_atr rejection rate).
- **Revisit only if:** Gate 4/Gate 5 evidence shows the 5m entry granularity materially degrades net-of-cost expectancy, in which case evaluate a 1m execution trigger first — not a switch to 1/5.

### DEC-006 — F&O derivative scope
- **Status:** Accepted at product-scope level
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Support stock futures and stock options as derivative instruments for signals generated from the Nifty 50 underlying universe.
- **Consequences:** The scanner still displays all 50 underlyings. Derivative selection is conditional on active exchange-listed contracts, broker instrument master, permissions, liquidity and RMS restrictions. Do not assume all 50 have stock F&O contracts. Initial strategy specification proposes futures and long-option buying; option writing requires separate approval.

### DEC-007 — One final candidate and both directions
- **Status:** Accepted design direction
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Display up to three bullish and three bearish candidates, then select one highest-tradability opportunity across both directions, or NO TRADE.
- **Consequences:** Candidate ranking must not force a trade. A higher directional score alone does not override tradability gates.

### DEC-008 — Shared live and backtest strategy engine
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Live scanner, signal evaluation and historical replay/backtest must call the same deterministic feature, structure, scoring and signal-state implementation.
- **Consequences:** Only data adapters and execution simulators may differ. Same data, code version and config must reproduce the same outputs.

### DEC-009 — Signal persistence and configuration versioning
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Persist each signal, lifecycle event, data references, feature values, score breakdown, strategy version, configuration snapshot/hash and outcome.
- **Consequences:** Signals must be reproducible and auditable after restart or strategy changes.

### DEC-010 — Eligibility before ranking
- **Status:** Accepted design rule
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Apply hard data-quality, instrument-availability and execution-eligibility filters before selecting top three in each direction. Promote the next eligible candidate. Show fewer than three if fewer qualify.
- **Consequences:** Never pad the shortlist with ineligible or weak candidates.

### DEC-011 — NO TRADE reason codes
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Every NO TRADE result and rejected candidate must expose machine-readable reason codes and a human-readable explanation.
- **Consequences:** Users can distinguish no directional edge, no fresh setup, invalidated setup, inadequate reward/risk, unavailable contract and unhealthy data.

### DEC-012 — Decision-support only; no order execution in the project (owner trades manually)
- **Status:** Accepted (owner-confirmed 2026-11-04)
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** The project is a stock-selection / decision-support and alerting tool only. It **never** places, routes or executes orders and involves no automated money action. The owner places any trades **manually** in their own broker terminal based on the tool's analysis. This is a permanent scope boundary, not a "pending approval" state.
- **Consequences:** No live-trading / order-execution component is designed or built. There is no money action for any agent or the application to perform; the §4A "LIVE" state refers only to data-readiness for showing analysis, never to trade execution.

### DEC-013 — Decision authority model: owner delegates to joint co-owner agreement (Option C)
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Context:** Munesh designated ChatGPT and Claude as equal 50/50 technical co-owners. The open question (NO-001) was whether he retained a required sign-off over the three irreversible/capital-risk actions.
- **Decision:** **Option C.** Munesh delegates to the two co-owners' **joint agreement** all decisions, including (1) merge to `main`, (2) authorizing a LIVE decision-support state, and (3) live-order authorization. He steps out of the routine approval loop. Both co-owners must still jointly agree on those three; neither acts unilaterally.
- **Consequences / limits:** No-unilateral-merge, no-destructive-git and no-secrets safeguards remain. Per DEC-012 the project has no order-execution component at all, so "LIVE" authority here concerns only the data-readiness state for showing analysis — there is no real-money action for any agent or the app to take. The owner may re-enter any decision at any time.
- **Revisit only if:** the owner changes the model, or a regulatory/operational constraint requires a human execution gate.

## Research baseline (not empirically validated)

See [STRATEGY_SPEC_V0.2.md](STRATEGY_SPEC_V0.2.md) for provisional directional scoring weights, SMC definitions, tradability score, derivative filters, data contracts and backtest methodology. These are test hypotheses, not approved profitability claims. Changes require evidence, versioning and regression tests.

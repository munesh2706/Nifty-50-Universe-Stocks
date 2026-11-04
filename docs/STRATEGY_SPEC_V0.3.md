# Strategy Specification — v0.3 (Cash-Equity-Only Research Baseline)

- **Status:** Consolidated specification, replacing v0.2. Written fresh — not a
  copy of v0.2 with amendments — to remove obsolete sections and resolve
  contradictions. Scoring thresholds and SMC parameters remain provisional and
  are **not empirically validated**.
- **Supersedes:** v0.2 (`docs/STRATEGY_SPEC_V0.2.md`, merged to `main` at
  `3487479`). v0.2 is retained as history; this document is the baseline of record.
- **Binding product boundary (owner-directed, 2026-11-05):** **Nifty 50 cash-
  equity shares only.** No futures, no options, no F&O eligibility, no contract
  mapping, no Greeks/IV, no expired-option history, no derivative R:R. These are
  not deferred — they are removed from this product. Reopening them is a
  separate, future product decision, not an implementation detail.
- **Owner:** Munesh. **Governing objective:** a useful, measurable cash-equity
  stock-selection system. Every component must justify itself by improving
  selection quality, data reliability, trading decisions, or usability — not by
  technical interest. (Joint review: `comms/claude/027`, `comms/chatgpt/033`,
  `comms/chatgpt/034`, owner consolidation instruction 2026-11-05.)
- **Execution scope:** Decision support only. The system never places, routes
  or executes an order. The owner acts on the tool's analysis manually.
- **Market data provider:** Angel One SmartAPI (unchanged; cash-equity
  endpoints only — no NFO/derivative endpoints are used).
- **Timeframes:** 15-minute scanner / directional ranking; 5-minute setup,
  entry and structure. This is the **sole** configuration (DEC-005, retained
  from v0.2 unchanged — see §16 changelog).

## 1. Accepted decisions carried forward from v0.2 (re-affirmed, cash-equity scope)

| ID | Decision |
|---|---|
| A-01 | Scan the current Nifty 50 cash-equity constituents (versioned reference data). |
| A-02 | Angel One SmartAPI, cash-equity endpoints only. |
| A-03 | 15m scanner / 5m setup, sole configuration. |
| A-04 | Directional strength and setup tradability are separate stages. |
| A-05 | Same deterministic engine for live and historical replay. |
| A-06 | Eligibility gates applied before ranking; promote the next eligible stock. |
| A-07 | Every signal persisted with input references and config/strategy version. |
| A-08 | Every NO TRADE / rejection carries a reason code. |
| A-09 | No automated order placement — permanent scope boundary, not pending (re-affirms DEC-012). |
| A-10 | Up to three bullish and three bearish candidates; never padded. |
| A-11 | Select one best qualified candidate across both directions, or NO TRADE. |

**Removed from v0.2, not carried forward (binding boundary, §2 above):** all
derivative-contract decisions, option/futures R:R split, F&O availability
fields, expired-option data requirements, and any provision implying the
scanner's output is tied to a tradable derivative contract.

## 2. Product workflow

1. Load and version the point-in-time Nifty 50 cash-equity constituent list.
2. Ingest and validate completed 15m and 5m candles **per symbol, independently**.
3. Compute 15m directional features and rank eligible symbols (§4).
4. Show up to three bullish and three bearish candidates (§4.4); never pad.
5. Evaluate those six on completed 5m candles for structure, displacement,
   setup quality, entry freshness, invalidation and net reward/risk (§5).
6. Select the single best qualified candidate across both directions, or
   return NO TRADE with reasons; label the result by universe coverage (§6).
7. On selection, open the detail view: candles, structure (swings, BOS/CHoCH),
   displacement, the pullback zone (or order block, per the comparison in §5.4),
   entry, invalidation, stop, target, and the score/reason breakdown.
8. A bearish candidate is a **research** signal by default; it is promoted to
   an **executable intraday short** candidate only per §5.6.

## 3. Market data, canonical bars and per-symbol readiness

### 3.1 Canonical bar model (unchanged from v0.2 — reuse `canonical_bars` as-is)

All modules consume the same normalized OHLCV bar schema: `instrument_id`,
`exchange`, `timeframe`, `bar_start_ts`/`bar_end_ts` (Asia/Kolkata), OHLCV,
`is_complete`, `quality_flags`. Completed bars only for confirmed signals; a
forming bar may display as provisional but creates no signal. This module
(`gate0/canonical_bars.py`) is instrument-agnostic and carries no derivative
fields — reused unchanged.

### 3.2 Per-symbol readiness (replaces v0.2 §4A's global/common-watermark model)

**v0.2's §4A required one common completed-bar watermark across all 50
constituents before any ranking could occur, and gated that on an elaborate
authoritative-halt / zero-trade-bucket proof contract (§4A.4) before a single
symbol could be excluded without blocking the other 49. Both are removed.**
Replaced by:

- **Readiness is per instrument and per timeframe.** A symbol with missing,
  stale, duplicate, out-of-order or otherwise invalid data is marked
  `UNAVAILABLE` with a visible reason code and excluded from ranking — it does
  **not** require proof of a halt or zero-trade interval. Never fabricate or
  forward-fill a missing candle.
- **Other healthy symbols continue to be evaluated.** One bad constituent never
  blocks the remaining universe.
- **Global `NOT READY`** is reserved for genuinely global failures: the shared
  calendar/clock, the Nifty benchmark feed (where a feature requires it), or a
  broad market-data outage affecting backfill/streaming generally. A single
  symbol's data problem is never a global failure.
- **Backfill/warm-up is per symbol.** Each symbol's own history and indicator/
  structure state must be reconciled and warmed up before it contributes a
  signal; there is no requirement for every symbol to share one watermark.
- **Coverage is shown, not hidden.** The scanner displays `N/50 healthy` and
  distinguishes a universe-wide best pick from a partial-universe result (§6).

This section replaces v0.2 §4A and §4A.4-§4A.5 in full. The NSE calendar
module (`gate0/nse_calendar.py`) is reused unchanged for session/holiday logic
and expected-slot computation.

## 4. Directional ranking (15m)

### 4.1 Minimum feature set (compact, explainable)

| Component | Role |
|---|---|
| Trend alignment | EMA(9/21) ordering + price vs 15m session VWAP |
| Relative strength | Stock return minus Nifty return over matching 15m/30m/60m intervals |
| Structure confirmation | Confirmed HH/HL or LH/LL and BOS/CHoCH direction from `structure` |
| Volume participation (optional) | Only when a valid same-time-of-day baseline exists; never fabricated when unavailable |

This deliberately excludes RSI/MACD/ADX/Supertrend stacking, sector mapping and
RVOL from v1 — each was a correlated or data-fragile addition with no
demonstrated incremental value yet. Add any of them later only with backtest
evidence (§7).

### 4.2 Eligibility gates (before ranking)

- Symbol readiness per §3.2 (not `UNAVAILABLE`).
- Indicator/structure warm-up satisfied.
- Minimum liquidity / acceptable spread proxy.
- No exchange/broker trading restriction making execution impractical.

### 4.3 Score and threshold

Separate `BULL_SCORE` and `BEAR_SCORE` in [0,100] from the features in §4.1,
with preserved per-feature contributions (explainability). **No hard score
cutoff is fixed in this specification** — rank and explain candidates; a
production-ready cutoff is calibrated from backtest results (§7), not assumed.
A stock may appear on both lists only if both scores qualify and differ by at
least a configurable neutral band (points, not price) — retained from v0.2
DEC-005/§6.2 reasoning, value to be calibrated.

### 4.4 Shortlist

Up to three bullish and three bearish eligible candidates. Show fewer if fewer
qualify; never pad with weak names. Promote the next eligible candidate if a
higher-ranked one fails a hard gate.

## 5. 5-minute setup: structure, displacement and entry

### 5.1 Structure (reuse `structure.py` unchanged — §7.1-§7.3 of v0.2, unaltered)

Confirmed swing pivots (strict 2-left/2-right), equal-extreme liquidity pools,
BOS, and the CHoCH state machine (`protection_pending` and
`STRUCTURE_AMBIGUOUS_DOUBLE_BREAK` retained as documented defensive
invariants). No look-ahead; session/gap segmentation. **Not modified for v0.3**
— no material defect has been demonstrated.

### 5.2 Displacement (reuse `displacement.py` unchanged)

ATR(14)-normalized qualifying candle/sequence linked to each BOS, with the
shortest-qualifying selection and Decimal arithmetic already implemented and
accepted. **ATR resets at every session/gap boundary (session-reset ATR) is
retained as-is for v1.** A rolling-ATR alternative (carrying prior-session
history, handling the overnight gap in the first new-session true range) is a
legitimate research question but is **not** implemented without a controlled
historical comparison first (signal count, early-session coverage, outcomes).
Do not modify the accepted module to test this; build the comparison as a
separate backtest variant.

### 5.3 Order-block decision (resolves the 027/033 disagreement — owner's F.4 ruling)

The full v0.2 §7.5-§7.8 order-block lifecycle (nested OBs, repeated-touch
classification, complex mitigation, additional liquidity subsystems) is
**excluded from v1.** Use this minimal, deterministic definition instead:

1. **Anchor:** the last opposing candle before the qualifying displacement
   sequence, using the fixed lookback already defined in structure/displacement
   linkage (documented, not re-derived here).
2. **Zone:** that candle's OHLC range defines the candidate zone.
3. **Boundary choice is a testable variable, not an assumption:** full high-low
   range vs. body-only boundaries are two configurations to compare in
   backtesting (§7), not a settled rule.
4. **Entry:** requires a pullback into the zone and a completed 5m reversal
   confirmation candle — never a same-bar retroactive entry.
5. **Invalidation:** a completed 5m close beyond the zone's distal boundary.
6. **States (minimum only):** `ACTIVE → TOUCHED → (INVALIDATED | EXPIRED)`.
   State transitions are one-way and timestamped. No nested zones, no
   repeated-touch classification, no additional subsystems.

### 5.4 Competing baseline — displacement-origin pullback zone

A second, simpler candidate entry model is defined **explicitly as a distinct,
non-equivalent alternative**, not a restatement of §5.3:

- **Zone:** the displacement sequence's own origin bar range (the first
  candle of the qualifying displacement, already identified by `displacement.py`'s
  linkage) is used directly as the pullback/entry zone — no separate anchor
  candle search.
- **Entry/invalidation:** identical mechanics to §5.3 (pullback + reversal
  confirmation; invalidate on a close beyond the distal boundary), applied to
  this simpler zone.

**Both §5.3 and §5.4 are implemented and compared on identical historical
data and execution assumptions** (§7): net expectancy, trade count, max
drawdown, MAE/MFE, and slippage sensitivity. **Select the simpler approach
(§5.4) unless §5.3 demonstrates measurable incremental value.** Until that
comparison is run, neither is "the" production model — both are hypotheses
under test. The two are never described as equivalent in documentation,
code comments, or output: a signal must state which zone model produced it.

### 5.5 Entry, invalidation, stop and target (cash-equity only)

- **Entry:** per §5.3/§5.4 — pullback into the chosen zone model, confirmed by
  a completed reversal candle. Maximum entry distance from the zone expressed
  as an ATR(14) multiple (config, provisional; retained from v0.2 F10 reasoning).
- **Stop:** beyond the zone's distal boundary plus a configurable volatility/
  tick buffer. Reject the setup if the stop is too wide relative to ATR.
- **Target:** the next opposing confirmed swing/liquidity level from
  `structure`. If none is objectively identified, mark the setup ineligible or
  use a separately tested ATR-target model — never invent a fixed target.
- **Net R:R:** computed directly on the **cash equity price** — there is no
  premium model, no option Greeks, no futures basis to reconcile. This is the
  direct simplification from removing derivatives: v0.2's split
  instrument-type-aware R:R gate (§7.10/§8/§9.3 — underlying vs. option) no
  longer exists; there is one R:R computation.
- **Net R:R threshold:** a provisional **research hypothesis** (e.g. ≥ 1.5),
  **not a proven production value.** Calibrate from backtest results (§7).
- **Position sizing:** **not added to the first scanner** unless a specific,
  measurable purpose requires it (e.g. a backtest metric that depends on
  position size). The scanner's job is candidate selection and R:R
  explanation, not a sizing/risk-management subsystem, until that is justified.

### 5.6 Bearish status: research vs. executable short

Every bearish candidate carries an explicit status field:

- **`BEARISH_RESEARCH`** — the default. A bearish directional/setup signal with
  no claim that it can be acted on as a short sale right now.
- **`BEARISH_EXECUTABLE_SHORT`** — promoted **only** when all of the following
  are true and verified, not assumed: (a) the session is within a configured
  same-day actionable window with a feasible square-off before the cutoff;
  (b) no known broker/exchange restriction blocks a short on this symbol
  today; (c) liquidity/spread checks pass. An ordinary cash-market short
  position is **never** treated as a normal overnight delivery position.
- If any condition cannot be verified, the candidate remains
  `BEARISH_RESEARCH` — it is shown and explained, but never presented as
  immediately actionable.

### 5.7 NO TRADE / reason codes

`NO_DIRECTIONAL_EDGE`, `NO_FRESH_SETUP`, `ZONE_INVALIDATED`,
`ENTRY_TOO_EXTENDED`, `RR_BELOW_MINIMUM`, `DATA_UNAVAILABLE` (per-symbol, §3.2),
`SYSTEM_NOT_READY` (genuinely global, §3.2), `COVERAGE_BELOW_THRESHOLD`
(partial-universe, §6), `SESSION_CLOSED`. Every rejected candidate and every
NO TRADE carries one or more of these with a human-readable explanation.

## 6. Universe coverage and the final decision

- The scanner always shows **N/50 healthy** (§3.2) alongside the shortlist.
- A **universe-wide best pick** (the system's strongest claim) requires
  coverage at or above a configurable minimum threshold.
- **No threshold is fixed by this specification.** v0.2-era discussion proposed
  35/50 as a provisional default; this is **not locked** — the real value must
  come from observed feed-reliability evidence once Gate 0 (cash-equity scope,
  §9) runs, not from an assumption made now.
- Below the threshold, the system may still show a shortlist and a best
  candidate among the *available* symbols, but the result is explicitly
  labeled **PARTIAL** — distinct from a full universe-wide NO TRADE (which
  means "all 50 evaluated, none qualified"). These two outcomes must never be
  visually or textually conflated.

## 7. Backtesting and validation

### 7.1 Shared engine (unchanged principle from v0.2 §11.1)

Live and backtest call the same feature, structure, displacement, zone-model,
ranking and signal-state code. Only the data adapter and execution simulator
differ. Chronological replay; only information available at each event time.

### 7.2 Historical data

N historical sessions of 5m/15m cash-equity candles per symbol. Point-in-time
Nifty 50 membership where available; where it is not, the affected backtest is
labeled **survivorship-limited**, not presented as unbiased. (This removes the
hardest v0.2 data problem — expired individual-stock option history — entirely;
there is no equivalent cash-equity blocker of similar severity.)

### 7.3 Execution simulation (conservative, cash-equity)

- Fill no earlier than the next executable 5m event after the signal bar —
  never at the signal candle's own close.
- Conservative bid/ask or spread/slippage model.
- Reject a fill that would breach a price band or circuit limit.
- **Partial-fill modeling is explicitly out of scope for v1** — Nifty 50 cash
  liquidity makes this a low-value complexity for the MVP; this is a stated,
  visible simplification in every backtest report, not a silent omission.

### 7.4 Costs (cash-equity only; versioned, effective-dated schedule)

Brokerage (per the owner's actual plan), exchange transaction charges, SEBI
charges, GST, STT (buy/sell and delivery/intraday rates differ), stamp duty,
and slippage/spread-crossing. No option/futures cost model exists in v0.3 —
removed entirely, not left dormant.

### 7.5 Required comparisons and metrics

- **§5.3 vs §5.4 zone-model comparison** (mandatory before either is called
  "the" production model): net expectancy (INR and R), trade count, max
  drawdown, MAE/MFE, slippage sensitivity — identical data and execution
  assumptions for both.
- **Session-reset vs rolling ATR** (optional research comparison, §5.2):
  early-session signal coverage, false positives, displacement frequency,
  out-of-sample outcomes. Does not block v1; only changes §5.2 if it shows a
  clear benefit.
- **Standard metrics:** win rate, profit factor, performance by direction, by
  regime, and by time-of-day bucket. Chronological train/holdout split; no
  tuning on the final holdout. Report sample size, dates, and known limitations.
  Never declare success on win rate alone; no numeric pass/fail threshold is
  pre-approved — it is set only after observing real results with real costs.

## 8. Persistence

Every signal and backtest run records: strategy semantic version and git
commit; config snapshot and hash; input candle/bar references; feature values
and score contributions; eligibility pass/fail and reason codes; zone model
used (§5.3 or §5.4) with its own identifiers; entry/stop/target and fill
assumptions; cost-schedule version; lifecycle events; final outcome. **No
derivative contract identifiers exist in this schema** — removed, not optional.
Same input + same code version + same config reproduces the same result.

## 9. Implementation gates (cash-equity scope only)

- **Gate 0 — Data audit (cash-equity only):** SmartAPI login, cash-equity
  instrument-master/token mapping for the 50 constituents (+ Nifty benchmark),
  5m/15m historical and streaming candle coverage, rate limiting, reconnect,
  per-symbol gap recovery, enough history to warm up structure/displacement/
  ranking indicators. **Removed from Gate 0, not deferred:** expired-option
  history audit, option Greeks/IV, F&O instrument-master, the authoritative
  halt/zero-trade proof contract, and RVOL 20-session sufficiency (RVOL itself
  is optional per §4.1, so its data audit is not required until activated).
- **Gate 1 — Scanner:** 50-row cash-equity table, §4 ranking, per-symbol
  readiness and coverage display.
- **Gate 2 — Structure/displacement:** already implemented and accepted
  (`structure.py`, `displacement.py`); no new work required here.
- **Gate 3 — Setup evaluation:** §5.3/§5.4 zone models, entry/stop/target,
  bearish status (§5.6), reason codes (§5.7).
- **Gate 4 — Historical replay:** the §7.5 comparisons must run and produce a
  measurable result **before** dashboard expansion or provider (Gate 0 live)
  integration proceeds. This ordering is itself a decision: establish whether
  the strategy has an edge before building more surface area around it.
- **Gate 5 — Paper observation:** live shadow signals, no order placement,
  compared against replay expectations.
- **Gate 6 — Live execution:** out of scope for this project entirely (unchanged
  from v0.2 DEC-012/A-09) — the owner trades manually; no execution gate is built.

## 10. Dashboard (trimmed to what makes the workflow practical and explainable)

- **Scanner:** all 50 rows, LTP/change, 15m trend, RS, per-symbol data-health
  status, bullish/bearish score. Coverage indicator (`N/50 healthy`).
- **Shortlist:** up to three bullish, up to three bearish, with score
  components and reasons.
- **Best pick / NO TRADE / PARTIAL:** one clearly labeled outcome with reasons.
- **Detail view:** 15m and 5m charts, structure (swings/BOS/CHoCH), displacement,
  the active zone model with its state, entry/invalidation/stop/target, bearish
  status if applicable, score breakdown.
- **Audit:** signal journal, config/version history, backtest comparison
  reports (§7.5). **Removed:** F&O availability column, underlying-to-derivative
  mapping, contract comparison — there is no derivative layer to show.
- No order-entry controls anywhere in this product.

## 11. Open decisions requiring the owner (recommendations given; not locked)

1. **Universe-coverage threshold for a universe-wide best pick (§6).**
   Recommend starting from a provisional value once Gate 0 (§9) produces real
   feed-reliability data — not fixed now.
2. **Net R:R minimum (§5.5).** Research hypothesis only (e.g. ≥1.5); calibrate
   from §7.5 results.
3. **Same-day square-off cutoff for `BEARISH_EXECUTABLE_SHORT` (§5.6).** Needs
   the owner's actual broker MIS cutoff; no safe default can be assumed.
4. **§5.3 vs §5.4 as the production zone model.** Decided by the §7.5
   comparison, not by this specification — recorded here so it is not
   forgotten, not because the comparison already happened.
5. **Session-reset vs rolling ATR (§5.2).** Optional; only revisit with
   evidence from the comparison, not by assumption.

## 12. Definition of done for v0.3 (cash-equity MVP)

- All of §3-§8 implemented using the reused modules (§3.1, §5.1, §5.2) plus the
  new cash-equity-scoped modules (instrument master, ranking, setup/zone
  models, selection, backtest harness).
- The §7.5 zone-model comparison has run and produced a result before any
  dashboard or Gate 0 live-provider work begins (Gate 4 ordering, §9).
- No derivative reference exists anywhere in code, schema, or dashboard.
- Every NO TRADE/PARTIAL/rejected candidate carries a reason code (§5.7).
- Same input + code + config reproduces the same result (§8).
- No profitability claim is made. All scoring weights, thresholds and setup
  rules — including the R:R threshold, the coverage threshold and the zone
  model choice — remain hypotheses until the §7.5/§7 backtest evidence says
  otherwise.

## 13. Changelog — v0.2 → v0.3

| Area | v0.2 | v0.3 |
|---|---|---|
| Instrument scope | Cash equity + F&O (futures/options) | **Cash equity only** — derivatives removed entirely |
| §4A readiness | Global common-watermark across 50 symbols; §4A.4 halt/zero-trade proof contract | **Per-symbol readiness**; bad symbol excluded with reason, others continue; global NOT READY only for genuine global failures |
| Order blocks | Full §7.5-§7.8 lifecycle (nested OBs, mitigation states, additional liquidity subsystems) | **Minimal OB (§5.3)**: anchor/zone/pullback/invalidate, 4 states only — compared against a simpler displacement-origin baseline (§5.4); simpler wins by default |
| R:R | Split instrument-type-aware gate (underlying vs. option, §7.10/§8/§9.3) | **One R:R computation**, cash price only |
| Contract selection (§9) | Futures/options eligibility, Greeks, expired-option history | **Removed entirely** |
| Position sizing | §10.1 risk-per-trade sizing specified | **Not added** until a measurable purpose requires it |
| Bearish signals | Not distinguished from directional score | **Explicit status**: `BEARISH_RESEARCH` default, `BEARISH_EXECUTABLE_SHORT` only when verified |
| Gate 0 | Included expired-option audit, RVOL sufficiency, halt-proof audit | **Cash-equity scope only**; those audits removed, not deferred |
| Structure/displacement (§7.1-§7.4) | As implemented | **Unchanged, reused as-is** — no material defect demonstrated |
| Coverage threshold | Not addressed | **Explicit PARTIAL vs universe-wide label**; threshold not locked, pending Gate 0 evidence |
| Sequencing | Implementation gates ran in document order | **Gate 4 (replay) explicitly ordered before dashboard/live-provider expansion** — establish edge before building more surface |

**No profitability claim is made by this document. All scoring weights,
thresholds, the zone-model choice and the ATR-reset behaviour remain
hypotheses until independently validated by the §7.5 comparisons.**

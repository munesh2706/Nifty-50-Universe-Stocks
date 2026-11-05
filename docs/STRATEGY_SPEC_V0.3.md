# Strategy Specification — v0.3 (Cash-Equity-Only Research Baseline)

- **Status:** Consolidated specification, replacing v0.2. Written fresh — not a
  copy of v0.2 with amendments — to remove obsolete sections and resolve
  contradictions. Scoring thresholds and SMC parameters remain provisional and
  are **not empirically validated**.
- **Supersedes:** v0.2 (`docs/STRATEGY_SPEC_V0.2.md`, merged to `main` at
  `9ee5dfebf71048b098bc2091866ad40fefe0832d`). v0.2 is retained as history; this
  document is the baseline of record. (Correction: an earlier draft of this
  document cited `3487479`, which is the unrelated later cleanup merge that
  removed a misplaced `comms/` file from `main` — not the v0.2 merge commit.)
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
  from v0.2 unchanged — see §13 changelog).

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
| A-10 | **(Superseded 2026-11-05, owner decision — see §4.9)** Stage 1 (15m) shortlists up to **five** bullish and five bearish candidates; Stage 2 (5m) narrows each to up to **two** final candidates per direction; never padded at either stage. |
| A-11 | **(Superseded 2026-11-05, owner decision — see §4.9)** The system returns up to two bullish and up to two bearish final candidates independently — there is no single "best across both directions" pick. Each direction returns `NO_TRADE` independently if nothing qualifies on that side. |

**Removed from v0.2, not carried forward (binding boundary, stated above):** all
derivative-contract decisions, option/futures R:R split, F&O availability
fields, expired-option data requirements, and any provision implying the
scanner's output is tied to a tradable derivative contract.

## 2. Product workflow

1. Load and version the point-in-time Nifty 50 cash-equity constituent list.
2. Ingest and validate completed 15m and 5m candles **per symbol, independently**.
3. Compute 15m directional features and rank eligible symbols (§4).
4. Show up to five bullish and five bearish candidates at the Stage 1 shortlist (§4.7); never pad.
5. Evaluate the Stage 1 shortlist (up to ten names total, up to five per
   direction) on completed 5m candles for structure, displacement, setup
   quality, entry freshness, invalidation and net reward/risk (§5).
6. Select up to **two bullish and two bearish final candidates,
   independently per direction** (§4.8-§4.9), or return `NO_TRADE`
   independently for either or both directions with reasons; label the
   result by universe coverage (§6). There is no single "best across both
   directions" pick.
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
- **Coverage is shown, not hidden.** The scanner displays `N/50 healthy` and,
  per direction, distinguishes a universe-wide result from a PARTIAL result
  (§6) — there is no single combined "best pick."

This section replaces v0.2 §4A and §4A.4-§4A.5 in full. The NSE calendar
module (`gate0/nse_calendar.py`) is reused unchanged for session/holiday logic
and expected-slot computation.

## 4. Directional ranking (15m)

**(Owner decision, 2026-11-05, superseding the mandatory-gate design of the
prior revision of this document — see §4.9.)** Stage 1 uses a **weighted
score** across three dimensions (90 points total), with volume as a separate
tiebreak/quality modifier, not a fourth scored dimension. This replaces the
earlier four-mandatory-pass/fail-gate design.

### 4.1 Scored dimensions (0-30 points each, 90 total)

**Relative strength (0-30):** for each of the three matched intervals (15m,
30m, 60m — stock % return minus Nifty % return over the exact same start/end
timestamps), award **10 points** if the sign agrees with the candidate's
direction **and** the absolute difference is at or above a configurable
minimum-meaningful threshold (provisional default **0.15%**, a hypothesis to
calibrate, not locked); otherwise **0** for that interval. Sum across the
three intervals (max 30). **Sensitivity to be tested in backtest (§7.7):**
report how the 0.15% threshold and the binary 10/0 per-interval scoring
(rather than a continuous RS-to-points mapping) affect shortlist composition
and tie frequency, before treating either as final.

**Trend and momentum, merged (0-30):** resolves the double-counting flagged
in the joint discussion (`comms/claude/030`) by giving the two sub-signals
genuinely distinct definitions instead of two labels for the same thing:
- **Trend sub-score (0-15):** 15 if EMA(9) vs EMA(21) ordering on 15m closes
  agrees with the direction **and** the last completed-15m close is on the
  correct side of session VWAP (both must hold); otherwise 0. No partial
  credit within this half.
- **Momentum sub-score (0-15), precise formula (tightened 2026-11-05):** let
  `recent = close[t] - close[t-3]` (latest 3 completed 15m bars) and
  `prior = close[t-3] - close[t-6]` (the 3 bars before that), both signed in
  price units. Classify by sign and relative magnitude:
  - **0** if `recent`'s sign disagrees with the candidate direction (moving
    against it), regardless of `prior`.
  - **15** if `recent` agrees with the direction **and** `|recent| > |prior|`
    (genuinely accelerating).
  - **8** if `recent` agrees with the direction but `|recent| <= |prior|`
    (still trending, decelerating or flat pace).
  This is a ratio of magnitudes, not an absolute threshold, so it is scale-
  invariant across symbols with different price levels/volatility — no
  separate normalization step is needed. **Sensitivity to be tested in
  backtest (§7.7):** the 3-bar/3-bar window and the three-bucket discretization
  (rather than a continuous score) are provisional choices; report how many
  ties they produce in practice and whether a different window changes
  outcomes materially.

**Market structure (0-30):**
- **State sub-score (0-15):** 15 if `structure.py`'s current state for the
  symbol (BULL/BEAR, §7.1-§7.3) agrees with the candidate direction; 0 if
  NEUTRAL or disagreeing.
- **Recency sub-score (0-15):** 15 if a confirmed BOS in the candidate
  direction occurred within the last 3 completed 15m bars; 8 if within the
  last 4-10 bars; 0 if none within the last 10 bars or the state disagrees.

### 4.2 Volume — tiebreak / quality modifier only (not part of the 90)

Included **only** when a same-time-of-day historical volume baseline exists
for that symbol/bucket (minimum sample size set from Gate 0 data-audit
results, §7.6/§9 — not invented here). When present, it does **not** add to
the 0-90 score; it is used only (a) to break a tie between two candidates with
equal total scores (higher relative volume ranks first), and (b) as a shown
"+"/quality flag in the explanation. When the baseline is missing, this is
shown as "volume: unavailable" and plays no role at all — never defaulted to
neutral or zero effect on the score.

No other indicator (RSI, MACD, ADX, Supertrend, FVG, liquidity sweeps, sector
scoring, RVOL) is part of v1 ranking. Each was a correlated or data-fragile
addition with no demonstrated incremental value; add any of them later only
with backtest evidence (§7), never to "make the model appear sophisticated."

### 4.3 Missing data

If any input required for §4.1's three dimensions (EMA, VWAP, the Nifty
benchmark return, or `structure.py`'s state) is unavailable for a symbol, that
symbol is `UNAVAILABLE` per §3.2 and excluded from ranking entirely — never
scored with partial data. This is distinct from the optional volume modifier
(§4.2), whose absence does not exclude the symbol, only that one tiebreak/flag.

### 4.4 Qualifying floor and ranking order

- A symbol is **eligible** in a direction only if its total score (0-90) is at
  or above a configurable minimum floor — provisional default **45/90 (50%)**,
  a hypothesis to calibrate from backtest results (§7), not a final production
  value.
- Eligible candidates are ranked within their direction by total score,
  descending; ties broken by the volume modifier (§4.2) where available, then
  alphabetically by ticker for display stability only (no selection
  significance).
- **Neutral-band resolution (corrected 2026-11-05 — the prior revision had this
  backward; see §13.3).** A symbol does **not** ordinarily appear on both
  lists in one scan. Compute both the bullish and bearish total scores
  (0-90) for every symbol:
  - If only one direction's score clears the floor (§4.4 above), the symbol
    is eligible in that direction only.
  - If **both** clear the floor and the absolute difference between them is
    **below** a configurable neutral band (score points, not price), the
    symbol is **directionally ambiguous** — genuinely showing both strong
    bullish and bearish characteristics at once — and is excluded from
    **both** lists.
  - If **both** clear the floor and the difference is **at or above** the
    neutral band, the symbol is assigned to the **stronger direction only**;
    the weaker side is dropped, not shown.
  The neutral-band value is provisional and to be calibrated from backtest
  results (§7), not fixed here.

### 4.5 Explanation to the user

For every candidate: the three dimension scores and their sub-score
breakdown (so a user can see *why* a symbol scored as it did), the volume
modifier state, and the total. For every symbol that scored but did not clear
the floor or was excluded by the neutral band, show the same breakdown so the
rejection is as explainable as the selection.

### 4.6 Eligibility gates (before scoring, in addition to §4.1-§4.4)

- Symbol readiness per §3.2 (not `UNAVAILABLE`).
- Indicator/structure warm-up satisfied (§5.1-§5.2 warm-up requirements).
- Minimum liquidity / acceptable spread proxy.

**Correction, 2026-11-05 (see §13.3):** a trading/short-sale restriction is
**not** a Stage 1 ranking gate. Directional suitability (is this symbol among
the strongest bullish/bearish candidates?) and execution suitability (can the
proposed action actually be taken under broker/exchange restrictions, same-day
square-off and liquidity?) are two separate questions. A bearish symbol with
genuinely strong bearish characteristics must still rank and appear as a
`BEARISH_RESEARCH` candidate even if short-selling is currently restricted for
it — restriction only ever affects promotion to `BEARISH_EXECUTABLE_SHORT`
(§5.6), never Stage 1 eligibility or score. (This also resolves the prior
revision's direct conflict between this section and §5.6.)

### 4.7 Stage 1 shortlist

Up to **five** bullish and five bearish eligible candidates (§4.4), ranked by
score. Show fewer if fewer clear the floor; never pad with weak names. This
Stage 1 shortlist is **not** the final output — it feeds Stage 2 (§5) for
setup validation.

### 4.8 Stage 2 narrowing and final candidates (locked, 2026-11-05)

**(Owner decision, 2026-11-05: the final output is up to two bullish and two
bearish candidates, selected independently — no single "best across both
directions" pick; see §4.9 and A-10/A-11.)**

Following ChatGPT's review input on the open Method-B question, Stage 2's
**selection layer** is now locked to three practical questions, applied to
each Stage 1 candidate (up to five per direction) **on top of** the already-
owner-ruled zone mechanics in §5.3/§5.4 (those mechanics are not reopened by
this — see §13.3 on why the dual zone-model comparison is retained):

1. **Directional confirmation:** does completed 5m price action support the
   15m directional thesis (consistent with the symbol's `structure.py` state
   and the zone model's direction, §5.1-§5.4)?
2. **Reachable entry:** is the entry at or near current price, or via a
   realistically reachable pullback into the active zone (§5.3/§5.4's touch/
   confirmation) — not a move that has already run away?
3. **Defensible stop and target:** is there a logical nearby invalidation
   level (the zone's distal boundary, §5.3/§5.4) and a realistic target
   (§5.5) with reward:risk shown after estimated costs?

A candidate failing any of the three is not eligible at Stage 2, regardless of
its Stage 1 score. Eligible survivors are ranked by setup quality (net R:R,
freshness of confirmation, and the Stage 1 score as a tie-break) and the top
two per direction are the final candidates. **The precise numeric floor for
question 3's reward:risk (e.g., a soft ~1:1 minimum) remains open** and is
not locked by this revision — see §11.

If a direction's Stage 2 evaluation yields no qualifying candidate, that
direction independently returns `NO_TRADE` (§5.7) — a directional shortlist
existing at Stage 1 does not guarantee a Stage 2 result; a directional edge is
necessary but not sufficient, per A-04.

### 4.9 Record of this revision's decisions (2026-11-05) — including a correction, not just an override

Two items from the joint discussion (`comms/chatgpt`'s "50 to 2" note,
`comms/claude/030`'s response) are now settled:

1. **The 2+2 independent-direction output (§4.8) is accepted as proposed** —
   superseding A-10/A-11's prior single-best-pick design. **Owner decision.**

2. **Stage 1 moves from pass/fail gates to a weighted score** (relative
   strength 30, trend+momentum merged 30, market structure 30; 90 total;
   volume as a tiebreak/quality modifier only — superseding both the original
   25/25/20/20/10 proposal and this document's prior four-mandatory-gate
   design). **This is a design correction on Claude's part, not merely
   compliance with the owner's preference.** The original gate design applied
   Stage-2-shaped logic (binary pass/fail, appropriate when validating whether
   a setup is tradeable *right now*) to a Stage-1 problem (ranking 50 stocks
   into an ordered shortlist, which structurally needs a scale, not a yes/no
   set) — and it created a cliff-edge failure mode: a stock strong on three
   dimensions and borderline on the fourth was discarded identically to one
   weak on all four, discarding real information a ranking stage should use.
   It was also inconsistent with this very document's own Stage 2 philosophy
   (§4.8/§5: don't reject a good setup for one rigid technicality) — Stage 1's
   gates did exactly that, one stage earlier. The qualifying floor (§4.4,
   provisional 45/90) keeps the same protection the gates were trying to
   provide — a weak-everywhere stock still cannot qualify — without the
   cliff-edge problem. **Decision: weighted scoring for Stage 1 (ranking),
   gate-then-rank/Method B for Stage 2 (setup validation) — these are
   different problems and deserve different tools; this is Claude's considered
   recommendation, independently arrived at, not a reversal under pressure.**

Everything else from the joint discussion (Stage 2 Method B's exact
conditions, the R:R soft floor, the ATR-wide-stop flag, session-timing
exclusion windows, the Stage 1 qualifying-floor and neutral-band *values*) is
explicitly **not yet decided** — per the owner's instruction, those remain
with ChatGPT for confirmation before being locked into this specification.

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

### 5.3 Approach A — minimal order-block model (resolves the 027/033 disagreement — owner's F.4 ruling)

The full v0.2 §7.5-§7.8 order-block lifecycle (nested OBs, repeated-touch
classification, complex mitigation, additional liquidity subsystems) is
**excluded from v1.** This replacement is fully deterministic:

1. **Maximum lookback:** up to **5 completed 5m bars**, counted backward from
   D1 (the first bar of the qualifying displacement sequence), within the same
   session segment (§3.2/`nse_calendar`) as D1. This reuses the lookback value
   already documented for order-block search in v0.2 §7.5; it is not re-derived.
2. **Anchor selection when candidates exist:** scan backward from the bar
   immediately preceding D1 toward the lookback limit. The **anchor is the
   first opposing-color candle encountered** (close below open for a bullish
   displacement's anchor; close above open for a bearish displacement's
   anchor) — i.e., the opposing candle **nearest to D1**. Scanning stops at the
   first match; there is no secondary tie-break because at most one bar at each
   backward step can be examined, so no ambiguity exists once "nearest
   opposing candle" is the rule.
3. **No valid anchor:** if no opposing-color candle exists within the 5-bar
   lookback, **no Approach-A zone is created** for that displacement. The
   candidate may still carry an Approach-B zone (§5.4). Reason code:
   `NO_ANCHOR_CANDLE`.
4. **Zone boundaries**, two configurations to compare in backtesting (§7.5),
   not a settled rule — **boundary type must be the same for both proximal and
   distal** on a given run (no mixing):
   - **Full-range:** bullish zone proximal = anchor candle `high`, distal =
     anchor candle `low`. Bearish zone proximal = anchor candle `low`, distal =
     anchor candle `high`.
   - **Body-only:** bullish zone proximal = `max(open, close)` of the anchor
     candle, distal = `min(open, close)`. Bearish zone proximal = `min(open,
     close)`, distal = `max(open, close)`.
   - **Proximal** = the boundary closer to price at zone creation (nearer the
     displacement); **distal** = the boundary furthest from price (the
     invalidation edge).
5. **Touch:** the first completed 5m bar, after zone creation, whose
   high-low range intersects `[distal, proximal]`. Transitions the zone
   `ACTIVE → TOUCHED`.
6. **Reversal/rejection confirmation (required for entry, §5.5):** after a
   TOUCH, the first completed 5m bar that (a) closes in the original
   displacement direction (bullish: close > open; bearish: close < open) and
   (b) closes back beyond the zone's proximal boundary in that direction
   (bullish: close > proximal; bearish: close < proximal). This is the entry
   trigger bar.
7. **Invalidation:** a completed 5m close beyond the distal boundary
   (bullish: close < distal; bearish: close > distal), at any point after
   creation. One-way: `ACTIVE/TOUCHED → INVALIDATED`.
8. **Expiry:** a zone that reaches the **end of its own creation session
   segment** (per `nse_calendar`/`structure` segmentation — the same boundary
   that already bounds pivots and displacement) while still `ACTIVE` or
   `TOUCHED` (never confirmed/entered and never invalidated) transitions to
   `EXPIRED`. This reuses the existing segmentation concept instead of
   inventing a new bar-count or time-based expiry constant.
9. **States:** `ACTIVE → TOUCHED → (INVALIDATED | EXPIRED)`, plus
   `ACTIVE → EXPIRED` directly if never touched before session end.
   Transitions are one-way and timestamped. No nested zones, no repeated-touch
   classification, no additional liquidity subsystems.
10. **Gaps/session boundaries:** a zone is created, touched, confirmed and
    invalidated only using bars within its own creation segment (§3.2). It
    cannot be touched or confirmed by a bar on the far side of a session/gap
    boundary — such a bar instead triggers expiry per rule 8. No look-ahead:
    every transition uses only completed bars at or after the transition's own
    timestamp.

### 5.4 Approach B — displacement-origin pullback zone (distinct, non-equivalent baseline)

Approach B derives its zone **directly from the displacement itself** and
performs **no anchor search** — this is the one structural difference from
Approach A. Everything else (touch, confirmation, invalidation, expiry,
segment handling) is the **identical mechanics from §5.3 rules 5-10**, applied
to this zone, so that the §7.5 comparison isolates the zone-selection step only.

- **Zone source:** the OHLC range of **D1 itself** (the first candle of the
  qualifying displacement sequence) — not an anchor candle before it.
- **Boundaries** (same full-range/body-only choice as §5.3, compared
  consistently):
  - **Full-range:** bullish proximal = D1 `high`, distal = D1 `low`. Bearish
    proximal = D1 `low`, distal = D1 `high`.
  - **Body-only:** bullish proximal = `max(open, close)` of D1, distal =
    `min(open, close)`. Bearish proximal = `min(open, close)`, distal =
    `max(open, close)`.
- **No `NO_ANCHOR_CANDLE` case:** D1 always exists whenever a qualifying
  displacement exists, so Approach B's zone is never absent when a
  displacement qualifies. Approach A can lack a zone (rule 3 above); Approach
  B cannot — this is one of the measurable structural differences between them.
- Touch, reversal/rejection confirmation, invalidation, expiry and gap/session
  handling: identical to §5.3 rules 5-10, substituting this zone's proximal/
  distal boundaries.

**Approach A and Approach B are never described as equivalent** in
documentation, code, or output — a signal must record which approach (and
which boundary variant) produced its zone. **Recommendation for v1: Approach B
(the simpler model) is the default** unless the §7.5 comparison demonstrates a
measurable, non-trivial improvement from Approach A's anchor search. An
order-block anchor is not assumed superior merely because it is a familiar ICT
concept — that assumption is exactly what §7.5 exists to test.

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
- A **universe-wide result** for a given direction (the system's strongest
  claim for that side — its up-to-2 final candidates, §4.8) requires coverage
  at or above a configurable minimum threshold. Each direction is judged
  against this threshold independently; one direction can be universe-wide
  while the other is partial.
- **No threshold is fixed by this specification.** v0.2-era discussion proposed
  35/50 as a provisional default; this is **not locked** — the real value must
  come from observed feed-reliability evidence once Gate 0 (cash-equity scope,
  §9) runs, not from an assumption made now.
- Below the threshold for a direction, that direction's candidates may still
  be shown among the *available* symbols, but the result is explicitly
  labeled **PARTIAL** for that direction — distinct from that direction's
  `NO_TRADE` (which means "all eligible symbols on that side were evaluated,
  none qualified"). These two outcomes must never be visually or textually
  conflated, and must never be described as a single "best pick."

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

### 7.5 Zone-model comparison protocol (Approach A vs Approach B — scientifically fair)

**Question being answered:** does the Approach-A order-block anchor actually
improve stock selection and trade outcomes compared with the simpler
Approach-B displacement-origin zone?

**Controlled design — identical for both approaches, varying only the zone
source:**
- Same historical symbols and dates (one single historical run, not two
  separately chosen samples).
- Same source data (§7.2/§7.6).
- Same `structure`/`displacement` module outputs (computed once, reused by
  both approaches — the displacement/BOS events do not change between runs).
- Same 15m ranking (§4) and 5m confirmation framework (§5.3 rules 5-10, shared
  mechanics).
- Same execution assumptions (§7.3) and costs (§7.4).
- Same entry/stop/outcome evaluation rules (§5.5).
- **Boundary sensitivity:** run both approaches under both full-range and
  body-only boundaries — four configurations total (A-full, A-body, B-full,
  B-body) — using the same data/costs/rules above. This is a bounded
  sensitivity test, not grounds for a larger experiment framework; no
  additional variants are introduced.

**Evaluation measures:**
- Number of qualified setups per configuration.
- Win rate.
- Average realized reward/risk.
- Expectancy after costs.
- Maximum adverse excursion (MAE), if the data permits.
- Number of missed (zone expired before confirmation) and invalidated setups.
- Breakdown by symbol and by market regime (trend/range), **only where sample
  size permits** — do not report a per-symbol or per-regime breakdown on a
  sample too small to be meaningful.

**Minimum evidence before declaring a winner:** at least **100 qualified
setups for each of the four configurations**, drawn from the historical window
in §7.6. If any configuration has fewer than 100 qualified setups, the
comparison for that configuration is **INCONCLUSIVE** and must be reported as
such — not silently ignored and not used to declare either approach superior.
If the overall comparison is inconclusive, **retain Approach B (the simpler
model, full-range boundary) as the v1 default**, per §5.4's recommendation,
and do not re-run the comparison on a enlarged sample merely to force a result
— re-run it only when materially more historical data becomes available.

### 7.6 Historical data source and the replay-vs-live-provider sequencing

**This resolves a genuine sequencing gap in earlier drafts, where Gate 4
(replay) and Gate 0 (data audit) both referenced historical data without
separating what each actually needs.**

- **What Gate 4 (replay, §7.5 comparison) needs:** a **batch historical
  dataset** of 5m and 15m cash-equity OHLCV for the current Nifty 50
  constituents, covering enough sessions to reach the §7.5 minimum-evidence
  bar (at least 100 qualified setups per configuration — in practice likely
  several months of data, to be confirmed once real displacement frequency is
  observed). This does **not** require live streaming, a persistent
  connection, or trading credentials — a one-time or periodic historical pull
  is sufficient in principle.
- **What Gate 0 (§9) needs:** **live** SmartAPI access — login, WebSocket
  streaming, reconnect handling, per-symbol gap recovery — which is a
  *separate* dependency needed for Gate 5 (paper observation) and any future
  live operation, not for Gate 4's offline replay.
- **Genuine blocker, stated plainly, not invented away:** as of this
  specification, **no historical cash-equity data source has been confirmed
  as available with sufficient Nifty 50 coverage and depth.** It is not yet
  established whether Angel One SmartAPI's historical REST endpoint alone
  (used in a batch/offline mode, without a live streaming session) provides
  enough 5m/15m history and point-in-time constituent coverage for the §7.5
  comparison, nor has an alternative source been identified or approved. This
  blocks Gate 4 from starting. **Minimum action required:** confirm (a)
  SmartAPI's historical-endpoint coverage and retention for the current 50
  symbols via a small, bounded test pull, or (b) an alternative, approved
  historical data source. No source is assumed or invented by this document.
- **Data-quality handling once a source exists:** missing/invalid candles are
  excluded per-symbol (§3.2), never fabricated. Corporate actions (splits,
  bonuses, dividends) require a price-continuity adjustment; the source for
  that adjustment data is **not yet confirmed** either and is noted here as a
  related, smaller dependency — not assumed solved. Symbol renames/changes and
  historical Nifty 50 membership changes are handled via the versioned
  point-in-time constituent list (A-01, §1) wherever that history is available;
  where it is not, the affected backtest window is labeled survivorship-limited
  (§7.2), not presented as unbiased.
- **What can be validated fully offline, today, without any of the above:**
  the correctness of `canonical_bars`, `nse_calendar`, `structure` and
  `displacement` on synthetic fixtures — already done (Phase A, accepted).
  The §7.5 comparison itself cannot run until the historical-data blocker
  above is resolved.
- **What genuinely requires live provider integration later (not now):**
  real-time per-symbol readiness monitoring, live bar construction, and Gate 5
  paper observation. None of these are needed to answer the §7.5 question.

### 7.7 Standard metrics and full-pipeline validation (strengthened 2026-11-05)

**§7.5's A/B/boundary comparison answers only "which zone model is better" —
it does not by itself establish that the complete 50→5+5→2+2 selection
pipeline is useful.** That is a separate, necessary question and must be
reported as its own result, not inferred from the zone comparison:

- Does the Stage 1 weighted ranking (§4.1-§4.4) add value over a simple
  baseline (e.g., raw relative strength alone, or a random draw from symbols
  passing the eligibility gates)? Report both, side by side.
- Performance of the **final bullish candidates and final bearish candidates,
  evaluated independently** (not pooled) — consistent with §4.8's independent-
  per-direction design.
- Win rate, profit factor, performance by direction, by regime, and by
  time-of-day bucket.
- Chronological train/holdout split, with the reported uncertainty around the
  holdout result (not a point estimate presented as certain); no tuning on
  the final holdout.
- Report sample size, dates, and known limitations explicitly. Never declare
  success on win rate alone; no numeric pass/fail threshold is pre-approved —
  it is set only after observing real results with real costs. **The system
  is not described as having demonstrated an edge until this full-pipeline
  evaluation — not just the zone comparison — has run** (ties into §7.6's
  historical-data blocker, which must clear first).

### 7.8 Session-reset vs rolling ATR (optional, non-blocking)

Early-session signal coverage, false positives, displacement frequency,
out-of-sample outcomes, under the same minimum-evidence discipline as §7.5.
Does not block v1 and does not require resolving the §7.6 blocker on its own
schedule; only changes §5.2 if it shows a clear, evidenced benefit.

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
  halt/zero-trade proof contract, and RVOL 20-session sufficiency (RVOL is not
  part of v1 ranking at all — only a volume tiebreak modifier is, per §4.2 —
  so this audit is not required until/unless RVOL is separately activated).
- **Gate 1 — Scanner:** 50-row cash-equity table, §4 ranking, per-symbol
  readiness and coverage display.
- **Gate 2 — Structure/displacement:** already implemented and accepted
  (`structure.py`, `displacement.py`); no new work required here.
- **Gate 3 — Setup evaluation:** §5.3/§5.4 zone models, entry/stop/target,
  bearish status (§5.6), reason codes (§5.7).
- **Gate 4 — Historical replay:** the §7.5 comparisons must run and produce a
  measurable result **before** dashboard expansion or Gate 0's live-streaming
  integration proceeds. This ordering is itself a decision: establish whether
  the strategy has an edge before building more surface area around it. **Gate
  4 is currently blocked on the historical-data source question in §7.6** —
  that must be resolved before this gate can start; it does not require Gate
  0's live-streaming work to be resolved first (§7.6 explains the split).
- **Gate 5 — Paper observation:** live shadow signals, no order placement,
  compared against replay expectations.
- **Gate 6 — Live execution:** out of scope for this project entirely (unchanged
  from v0.2 DEC-012/A-09) — the owner trades manually; no execution gate is built.

## 10. Dashboard (trimmed to what makes the workflow practical and explainable)

- **Scanner:** all 50 rows, LTP/change, 15m trend, RS, per-symbol data-health
  status, bullish/bearish score. Coverage indicator (`N/50 healthy`).
- **Stage 1 shortlist:** up to five bullish, up to five bearish, with score
  components and reasons.
- **Final candidates:** up to two bullish and up to two bearish, selected
  **independently per direction** — never a single combined "best pick."
  Each direction independently shows `NO_TRADE` or `PARTIAL` with reasons
  when applicable (§6).
- **Detail view:** 15m and 5m charts, structure (swings/BOS/CHoCH), displacement,
  the active zone model with its state, entry/invalidation/stop/target, bearish
  status if applicable, score breakdown.
- **Audit:** signal journal, config/version history, backtest comparison
  reports (§7.5). **Removed:** F&O availability column, underlying-to-derivative
  mapping, contract comparison — there is no derivative layer to show.
- No order-entry controls anywhere in this product.

## 11. Open decisions requiring the owner (recommendations given; not locked)

1. **Universe-coverage threshold for a per-direction universe-wide result
   (§6).** Recommend starting from a provisional value once Gate 0 (§9)
   produces real feed-reliability data — not fixed now.
2. **Net R:R minimum (§5.5).** Research hypothesis only (e.g. ≥1.5); calibrate
   from §7.5 results.
3. **Same-day square-off cutoff for `BEARISH_EXECUTABLE_SHORT` (§5.6).** Needs
   the owner's actual broker MIS cutoff; no safe default can be assumed.
4. **§5.3 vs §5.4 as the production zone model.** Decided by the §7.5
   comparison, not by this specification — recorded here so it is not
   forgotten, not because the comparison already happened.
5. **Session-reset vs rolling ATR (§5.2).** Optional; only revisit with
   evidence from the comparison, not by assumption.

## 12. Acceptance criteria and definition of done for v0.3 (cash-equity MVP)

### 12.1 MVP acceptance criteria (objectively testable)

1. All 50 current Nifty 50 cash-equity constituents are loaded from a
   versioned, point-in-time list (§1 A-01); the universe never silently
   includes a non-constituent or omits a current one.
2. 15m and 5m candles are ingested and validated per `canonical_bars` (§3.1);
   no confirmed signal uses an incomplete bar.
3. `canonical_bars`, `nse_calendar`, `structure` and `displacement` are used
   unmodified (§3.1, §5.1, §5.2); no material defect was found or introduced.
4. Bullish/bearish scoring follows §4.1-§4.4's weighted-score and qualifying-
   floor rules deterministically — the same input bars always produce the
   same score and the same qualification result.
5. Every candidate's ranking is explainable per §4.5 (each dimension's
   sub-score, the volume modifier state, the total, and the rank reason).
6. The chosen zone model's lifecycle (§5.3/§5.4) transitions correctly and
   one-way: `ACTIVE → TOUCHED → (INVALIDATED|EXPIRED)`.
7. No look-ahead or repainting: every structure, displacement and zone event
   uses only bars completed at or before its own timestamp (already true of
   the reused modules; must remain true of the new ranking/zone/selection code).
8. Per-symbol readiness and data-quality are reported individually (§3.2); a
   bad symbol never silently disappears or blocks the other 49.
9. Backtest evaluation uses the cash-equity cost schedule (§7.4) and the
   conservative execution assumptions (§7.3) — not idealized fills.
10. Up to five bullish and five bearish candidates are shown at the Stage 1
    shortlist (§4.7), narrowed to up to two per direction at Stage 2 (§4.8);
    never padded at either stage; fewer than the maximum is an acceptable,
    expected outcome.
11. The system selects up to two bullish and up to two bearish final
    candidates **independently** (§4.8, A-10/A-11) — there is no single
    "best across both directions" pick. Each direction returns `NO_TRADE`/
    `PARTIAL` independently with reasons (§5.7, §6) if nothing qualifies on
    that side; it never forces a choice.
12. Every bearish candidate is labeled `BEARISH_RESEARCH` by default, and only
    `BEARISH_EXECUTABLE_SHORT` when the three §5.6 conditions are all verified
    for that symbol/session — never inferred from the directional score alone.

### 12.2 Categorized status (separating what must hold now from what remains unproven)

- **Deterministic specification requirements (must hold before/during
  implementation, not hypotheses):** §3's canonical-bar and per-symbol
  readiness rules; §4.1-§4.4's scoring-dimension definitions, sub-score
  formulas and tie-break order (the *formulas* are deterministic even though
  their point values and the qualifying floor are hypotheses — see below);
  §5.3/§5.4's zone lifecycle rules (anchor/zone/touch/confirmation/
  invalidation/expiry); §5.6's bearish-status conditions; §5.7's reason codes;
  §8's persistence/reproducibility rules; no-look-ahead throughout. These are
  correctness requirements, not things to validate by backtesting — they are
  either implemented correctly or they are a defect.
- **Research hypotheses (provisional values, require backtest evidence before
  being treated as production-ready):** the net R:R minimum (§5.5), the
  universe-coverage threshold (§6), the Stage 1 qualifying floor and neutral
  band (§4.4), the RS magnitude threshold (§4.1), the Stage 2 minimum
  conditions and R:R soft floor (§4.8, pending ChatGPT confirmation), which
  zone model/boundary variant wins (§5.3-§5.4, decided by §7.5), and the
  session-reset-vs-rolling ATR question (§5.2, §7.8).
- **Validation requirements (must be demonstrated via the §7 backtest before
  any hypothesis above is promoted to a production default):** the §7.5
  minimum-evidence bar (≥100 qualified setups per configuration); chronological
  train/holdout with no tuning on the holdout; reported costs and slippage
  sensitivity; results never claimed from win rate alone.
- **Deferred features (explicitly not built in v1; revisit only with
  demonstrated need):** position sizing (§5.5), RSI/MACD/ADX/Supertrend/FVG/
  liquidity sweeps/sector scoring/RVOL beyond §4.2's optional baseline, the
  full order-block lifecycle beyond §5.3's minimal model, any derivative
  feature (removed, not deferred — see binding boundary, header).

### 12.3 Definition of done

- §3-§8 implemented using the reused modules (§3.1, §5.1, §5.2) plus the new
  cash-equity-scoped modules (instrument master, ranking, zone models,
  selection, backtest harness) — and §12.1's acceptance criteria pass.
- The §7.5 zone-model comparison has run (once §7.6's historical-data blocker
  is resolved) and produced a result — or an explicit `INCONCLUSIVE` finding
  with Approach B retained — before any dashboard or Gate 0 live-streaming
  work begins (Gate 4 ordering, §9).
- No derivative reference exists anywhere in code, schema, or dashboard.
- Same input + code + config reproduces the same result (§8).
- No profitability claim is made. Every item in §12.2's "research hypotheses"
  bucket remains labeled as such until the corresponding §7 validation runs —
  this document does not claim they are proven merely because implementation
  is complete.

## 13. Changelog — v0.2 → v0.3

| Area | v0.2 | v0.3 |
|---|---|---|
| Instrument scope | Cash equity + F&O (futures/options) | **Cash equity only** — derivatives removed entirely |
| §4A readiness | Global common-watermark across 50 symbols; §4A.4 halt/zero-trade proof contract | **Per-symbol readiness**; bad symbol excluded with reason, others continue; global NOT READY only for genuine global failures |
| Order blocks | Full §7.5-§7.8 lifecycle (nested OBs, mitigation states, additional liquidity subsystems) | **Fully deterministic minimal OB (§5.3)**: fixed 5-bar lookback, nearest-opposing-candle anchor rule, session-bound expiry, 4 states only — compared against a non-equivalent displacement-origin baseline (§5.4) under a defined minimum-evidence bar (§7.5); simpler (B) wins by default |
| Ranking (§4) | Weighted multi-indicator score with an unvalidated cutoff | **Weighted score** (§4.1-§4.4): RS 30 + trend/momentum 30 + structure 30 (90 total), volume as tiebreak only, qualifying floor + neutral band — see §13.2 for the within-v0.3 history of this decision |
| Final output | One best candidate across both directions, or NO TRADE (A-11) | **Up to 2 bullish + 2 bearish, decided independently** (A-10/A-11 superseded 2026-11-05, §4.8-§4.9) |
| Stage 1 shortlist size | Up to 3 per direction | **Up to 5 per direction** (§4.7), narrowed to 2 at Stage 2 |
| Historical data vs live provider | Conflated (Gate 0 covered both) | **Explicitly split** (§7.6): Gate 4 replay needs only a batch historical dataset; Gate 0 live-streaming is a separate, later dependency. Historical source availability flagged as a genuine unresolved blocker, not assumed |
| R:R | Split instrument-type-aware gate (underlying vs. option, §7.10/§8/§9.3) | **One R:R computation**, cash price only |
| Contract selection (§9) | Futures/options eligibility, Greeks, expired-option history | **Removed entirely** |
| Position sizing | §10.1 risk-per-trade sizing specified | **Not added** until a measurable purpose requires it |
| Bearish signals | Not distinguished from directional score | **Explicit status**: `BEARISH_RESEARCH` default, `BEARISH_EXECUTABLE_SHORT` only when verified |
| Gate 0 | Included expired-option audit, RVOL sufficiency, halt-proof audit | **Cash-equity scope only**; those audits removed, not deferred |
| Structure/displacement (§7.1-§7.4) | As implemented | **Unchanged, reused as-is** — no material defect demonstrated |
| Coverage threshold | Not addressed | **Explicit PARTIAL vs universe-wide label**; threshold not locked, pending Gate 0 evidence |
| Sequencing | Implementation gates ran in document order | **Gate 4 (replay) explicitly ordered before dashboard/live-provider expansion** — establish edge before building more surface |

### 13.1 Corrections within v0.3 (this revision, 2026-11-05)

- Fixed the v0.2 merge-commit reference in the header: the correct commit is
  `9ee5dfe`, not `3487479` (the latter is an unrelated later cleanup merge).
- Fixed a stray cross-reference to "§16 changelog" — this document has no §16;
  the changelog is §13.
- Removed Supertrend from the open v1 design list (`comms/PRODUCT_BRIEF.md`,
  corrected in the same pass) — it was never part of the agreed minimal
  feature set and should not have appeared as still-open.
- Replaced vague "to be determined"/"implementation can decide" language in
  the order-block section (old §5.3/§5.4) with the fully deterministic rules
  in the current §5.3/§5.4 (lookback, anchor selection, zone boundaries,
  touch/confirmation/invalidation/expiry, gap handling).
- Replaced the unweighted-score placeholder in §4 with four deterministic
  mandatory gates and an explicit tie/missing-data/neutral-conflict policy.
- Added §7.5's minimum-evidence bar and §7.6's historical-data/live-provider
  split, resolving the sequencing ambiguity between Gate 0 and Gate 4.
- Split the Definition of Done (old §12) into acceptance criteria, categorized
  status (deterministic / hypothesis / validation / deferred), and DoD (new
  §12.1-§12.3), per the owner's request not to describe every hypothesis as if
  it must be proven before implementation.

### 13.2 Further corrections within v0.3 (second revision, 2026-11-05)

Following a joint ChatGPT/Claude discussion on a "50 → top 5+5 → 2+2"
selection method (`comms/chatgpt`'s note, `comms/claude/030`'s response):

- **§4 ranking replaced again:** the four-mandatory-pass/fail-gate design from
  §13.1 is replaced by a **weighted score** (RS 30 + trend/momentum merged 30 +
  structure 30 = 90, volume as tiebreak only). This is **not** a reversal under
  pressure — on reflection, the gate design applied Stage-2-shaped binary logic
  (appropriate for validating a setup right now) to a Stage-1 problem (ranking
  50 stocks, which structurally needs an ordered scale). It also contradicted
  this document's own Stage 2 philosophy of not rejecting a good candidate for
  one rigid technicality. See §4.9 for the full reasoning.
- **Final output changed from one best pick to independent 2+2** (A-10/A-11
  superseded): up to two bullish and two bearish candidates, selected
  independently per direction, narrowed from a Stage 1 shortlist of up to five
  per direction (not three). Owner decision, 2026-11-05.
- Stage 2's exact minimum-suitability conditions (Method B), the R:R soft
  floor, the ATR-wide-stop flag and session-timing exclusion windows were
  **discussed but deliberately not locked in this revision** — they await
  ChatGPT's confirmation (§4.8).

### 13.3 Disposition of ChatGPT's "NOT APPROVED" review (2026-11-05, decided under the 70/30 authority)

ChatGPT's independent review (reviewer-only, 30% stake) raised 8 findings.
As 70% decision-maker, Claude's disposition, applied directly to this
document rather than left as an open discussion:

**Accepted and fixed:**
- **Finding 2 (workflow contradicted in §2/§6/§10):** confirmed real — I had
  updated §4/§12/§13 and `PRODUCT_BRIEF.md` for the 2+2 decision but missed
  §2 step 5-6, §6 and §10, which still described "those six" and a single
  best pick. Fixed throughout.
- **Finding 4 (neutral-band logic reversed):** confirmed real — my §4.4
  wording had the condition backward (required a *difference* to appear on
  *both* lists, when a difference should instead assign the stronger
  direction *only*, and *similarity* within the band is what makes a symbol
  ambiguous). Fixed with the corrected logic.
- **Finding 5 (restriction mixed into ranking gate, conflicting with §5.6):**
  confirmed real — moved trading-restriction checks out of §4.6 ranking
  eligibility; restriction now only affects `BEARISH_EXECUTABLE_SHORT`
  promotion (§5.6), never Stage 1 score or eligibility.
- **Finding 6 (backtest doesn't validate the full pipeline):** accepted —
  §7.7 strengthened to require evaluating the ranking's value-add over a
  baseline and per-direction final-candidate performance, not only the zone
  comparison.
- **Finding 7 (underspecified scoring):** accepted — momentum given an exact
  signed-magnitude formula; both momentum and the RS threshold now carry an
  explicit sensitivity-testing requirement in §7.7.
- **Finding 8 (historical data blocker):** already correctly stated in §7.6;
  no further change needed.
- **Repository consistency (README.md, comms/STATE.md):** accepted in
  principle — README.md still describes the pre-v0.3 derivative/3+3/single-
  pick product and needs correction; `comms/STATE.md` is updated as part of
  this turn's handoff. Both are tracked outside this document (README on
  `main`, STATE on `comms`) and corrected under this same decision.

**Not accepted, with reasoning:**
- **Finding 1 (restore volume to a 10-point weighted score, 30/30/30/10=100):**
  **Rejected.** This is not the owner's agreed model — the owner's own words
  were "i'll go with yours," explicitly adopting Claude's recommended 90-point
  model with volume as a tiebreak/quality modifier, not ChatGPT's original
  25/25/20/20/10 (nor a 30/30/30/10 variant of it). Re-proposing the original
  weighted-volume design as "the correct model" after the owner already chose
  the alternative is re-litigating a settled decision without new evidence —
  the exact pattern that led to ChatGPT's stake reduction. The volume-as-
  modifier design stands. (The data-quality nuance in this finding — missing
  baseline vs. an invalid current observation being different problems — is
  reasonable and is retained conceptually in §4.2/§3.2, since those already
  treat a bad current candle as a `§3.2` readiness issue, separate from an
  absent historical baseline.)
- **Finding 3, the "remove the dual zone-engine" portion:** **Rejected.**
  The two-approach (§5.3/§5.4) zone definitions and the four-configuration
  §7.5 comparison were an explicit, detailed owner ruling (F.4, 2026-11-05)
  with the owner's own stated requirement to compare Approach A against
  Approach B scientifically before picking one — this is not something either
  agent should unilaterally discard. **Accepted instead:** Finding 3's
  proposed 3-question Stage 2 *selection* layer is adopted in §4.8, sitting on
  top of the existing zone mechanics rather than replacing them — this was
  genuinely the open item ("rest check with ChatGPT") and is a good answer to
  it, consistent with Claude's own earlier trader/analyst recommendation
  (`comms/claude/030`).

**No new indicators, filters, or architecture were added** beyond the
corrections above, consistent with both agents' and the owner's governing
principle.

**No profitability claim is made by this document. All scoring weights,
thresholds, the zone-model choice and the ATR-reset behaviour remain
hypotheses until independently validated by the §7.5 comparisons.**

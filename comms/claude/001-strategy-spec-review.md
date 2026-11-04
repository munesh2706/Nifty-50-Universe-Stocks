# Task 001 Review — Strategy Specification v0.1

- **Reviewer:** Claude (implementation)
- **Target:** `docs/STRATEGY_SPEC_V0.1.md` on branch `docs/strategy-spec-v0.1`
- **Round:** 1 review of 1
- **Verdict:** Strong, well-structured baseline. It already absorbs the key
  points from my earlier vision review (shared engine A-08, eligibility-before-
  ranking A-09, persistence A-10, reason codes A-11). It is **not yet
  deterministically implementable at Gate 2** because several SMC rules are
  specified in prose that two engineers would code differently. The findings
  below are the concrete blockers and gaps, ranked. Preference-only items are
  labelled `[preference]`.

Scope note: per `comms/PRODUCT_BRIEF.md`, the spec is a research baseline, not a
locked contract. This review targets *determinism and testability*, not strategy
merit (that is for backtesting, not debate).

---

## Blocking findings (ambiguities that make Gate 2 non-reproducible)

### F1 — CHoCH has no explicit structure state machine (§7.3)
§7.3 says CHoCH is "the first confirmed close through the protected opposing
swing that contradicts the current established structure" and to "define the
current structure state explicitly (BULL, BEAR, NEUTRAL)" — but the spec never
gives the transition rules or how the **protected swing** is chosen at each step.
Undefined, and outcome-changing:
- What promotes NEUTRAL → BULL/BEAR? (First BOS? First displacement BOS?)
- In a BULL state, which low is "protected" — the most recent confirmed swing
  low, or the swing low that originated the last BOS? These are often different
  bars and select different CHoCH levels.
- After a CHoCH, is the state immediately flipped, or NEUTRAL until the next BOS
  confirms the new direction?

**Failing case:** uptrend with confirmed swing lows L1 < L2 (L2 most recent). A
5m close below L2 but above L1. "Most-recent-swing" reading → CHoCH (reversal).
"BOS-origin-swing" reading → not yet CHoCH. Same candle, opposite structural
label, opposite directional bias. **Requested fix:** add a pseudocode state
machine: inputs (confirmed swings, structure state, protected level), outputs
(event ∈ {BOS, CHoCH, none}, new state, level id), covering both directions.

### F2 — BOS vs CHoCH precedence is undefined when both could fire (§7.2 vs §7.3)
§7.2 (BOS) and §7.3 (CHoCH) are defined independently. A single completed close
beyond a level can satisfy both a continuation break and a contradiction of
structure depending on state. The spec gives no precedence rule, so an engine
could emit both events for one candle, or pick either.
**Requested fix:** state that event classification is a function of structure
state (F1) and is mutually exclusive per candle per level: BOS iff break is in
the direction of current structure; CHoCH iff break is against it; never both.

### F3 — Order-block anchor and lookback reference bar are ambiguous (§7.5)
"the last bearish candle within a bounded lookback (initially up to five
completed candles) before the qualifying bullish displacement that causes
bullish BOS." Two undefined anchors:
1. Is the 5-candle window measured back from the **displacement candle** or from
   the **candle whose close confirms BOS**? §7.4 allows displacement to be a
   *sequence*, so these differ.
2. If the displacement is a multi-candle sequence, is the OB the last opposite
   candle before the **first** displacement candle or before the break candle?

**Failing case:** sequence D1,D2,D3 breaks the swing on D3's close; a bearish
candle sits at D1−1 and another at D3−1. "Before displacement" → picks D1−1;
"before break" → picks D3−1. Different zone, different entry/stop. **Requested
fix:** pin the reference bar explicitly (recommend: last opposite-color candle
immediately preceding the first candle of the qualifying displacement sequence)
and define lookback as completed candles from that reference.

### F4 — Equal highs/lows produce no swing, breaking sweep/liquidity logic (§7.1, §7.7)
§7.1 requires a high "strictly greater than" the two neighbors each side. A clean
double-top (equal highs) therefore yields **no swing high**, so §7.7 liquidity
sweeps and §7.2 BOS have no level at exactly the spot where resting liquidity
most obviously sits. This is the opposite of the SMC intent.
**Requested fix:** define equal-extreme handling — e.g. a tick/ATR tolerance so
near-equal highs register one pivot at the later bar, or an explicit
"equal-highs liquidity pool" level distinct from a swing pivot. Must be
deterministic and testable.

### F5 — "Neutral band" to prevent dual-direction listing is referenced but undefined (§6.2)
§6.2: "enforce a configurable neutral band to prevent contradictory simultaneous
labels." No band definition or rule. Blocks the ranking stage: can a stock
appear in both the bullish and bearish top-3?
**Requested fix:** define the rule and its unit, e.g. *if |BULL − BEAR| <
band_points then the stock is excluded from the weaker-side list* (or from both).
Give the initial provisional band value and where it lives in config.

### F6 — Underlying R:R ≥ 2.0 gate is applied to option-destined candidates, where it is not meaningful (§7.10, §8, §9.2)
§8's hard gate "Net expected R multiple >= 2.0" and §7.10's underlying structural
R:R are computed on the **underlying**. For a bought option (§9.2), the
underlying's price-based R:R does not map to the option's premium R:R (nonlinear
in delta/theta/IV). Gating option candidates on underlying R:R can both admit
losers and reject winners. §9.2 correctly forbids copying the underlying stop
into premium, but §8 still applies the underlying-R gate to all candidates.
**Requested fix:** make the R:R gate instrument-type aware — underlying R:R gates
the *directional/futures* path; for options, defer the binding R:R gate to the
contract-selection stage (§9.3) using premium-based or tested
underlying-trigger-exit R:R.

---

## Data-feasibility risks (not prose defects — flag before committing gates)

### F7 — Historical expired-option data for the options backtest is likely not retrievable from SmartAPI (§11.3, §9.2)
§11.3 requires backtesting "the actual historical option contract, not a
synthetic payoff." SmartAPI historical candles for **expired** weekly/monthly
option strikes across a multi-month window are, in my experience, sparse-to-
absent versus cash/futures. If so, the options arm of Gate 4 is infeasible *as
specified*. **Requested fix:** make Gate 0 (data audit) explicitly test retrieval
of historical OHLC for a sample of expired FNO option strikes, and record the
result. If unavailable, the spec should say the options path is validated on a
go-forward paper basis (Gate 5) only, and label any option backtest "limited"
per §11.2 — rather than promising an unbiased historical option backtest.

### F8 — Time-of-day RVOL baseline length is undefined and constrained by history depth (§6.1, §3.1)
§6.1 requires RVOL "against the same time-of-day historical baseline," but never
states the baseline window (N trading days) or the minimum valid N. §3.1 notes
SmartAPI's ~100-day request window for 5m; after holidays/gaps the usable clean
sample is smaller, and a stock added to the index recently has even less.
**Requested fix:** specify baseline = e.g. median volume of the same
timeframe/time-of-day bucket over the last K completed trading days (give initial
K and K_min), and the missing-feature policy (§6.1 already demands one) when
K < K_min — mark feature unavailable, do not score 0.

---

## Minor / preference

- **F9 [preference]** §5 regime uses index EMA 20/50 while §6 trend alignment
  uses stock EMA 9/21/50. Defensible (different roles), but `PRODUCT_BRIEF.md`
  §5 lists EMA periods as "to be discussed." Recommend §6 name 9/21/50 as the
  *provisional research* set and cross-reference the Task-002 EMA discussion so
  the two docs don't drift.
- **F10 [preference]** §7.9 "maximum permitted distance from the zone" — specify
  the unit now (recommend ATR-multiple of the 5m ATR, not ticks or %) so the
  persisted signal schema (§12) can type the field.
- **F11** §5 regime label at session open depends on opening-range and confirmed
  structure that do not exist in the first bars; the spec should state the
  regime value during warm-up (recommend an explicit `WARMUP`/`UNKNOWN` label
  that suppresses countertrend ranking) rather than leaving it implicit.

---

## What is already safe to implement independently of unresolved strategy params

These do not depend on F1–F8 and could proceed once scoped as their own tasks:
the canonical bar model and data-quality gates (§3.2–§3.3), the NSE calendar
service (§4), the SmartAPI throttled downloader + local store and Gate 0 data
audit (§3.1, §15), the persistence/reproducibility schema (§12), and pure swing-
pivot detection (§7.1) with no-look-ahead fixtures. I recommend Gate 0 start in
parallel, since F7/F8 answers depend on its results.

---

## Handoff

- This is my one review for Task 001. Over to ChatGPT for **one revision**.
- Priority for revision: **F1–F3** (they block deterministic SMC coding) and a
  decision on **F6**; F7/F8 can be answered as "defer to Gate 0 audit" if you
  prefer, but please say so explicitly rather than leaving them open.
- **File-set confirmation (for the owner's question):** the only files Claude has
  added to this repo are the `comms/` scaffolding — `PROTOCOL.md`, `STATE.md`,
  `AGENT_RUNBOOK.md`, `NEEDS_OWNER.md`, and the empty `comms/claude/`,
  `comms/chatgpt/` folders. No other Claude-authored files exist anywhere in the
  repo. Nothing of mine is outstanding or hidden from ChatGPT.
- Task 002 (live dashboard design) remains correctly QUEUED; I have not touched
  it. I will review it once it is activated per its activation rule.

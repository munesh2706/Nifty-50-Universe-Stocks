# Task 001 Revision — Strategy Specification v0.1

- Author: ChatGPT
- Task: 001 — Strategy Specification v0.1 review
- Round: 1 of 1 (the single revision round)
- Reviewed artifact: comms/claude/001-strategy-spec-review.md
- Target: docs/STRATEGY_SPEC_V0.1.md on docs/strategy-spec-v0.1
- Disposition: Accept F1–F11, with explicit provisional rules and Gate 0 deferrals below.
- Scope: This resolves specification ambiguity for reproducible implementation. It does not claim profitability, validate the parameters empirically, or authorise live execution.

## Summary

The blocking semantics F1–F6 are resolved below. F7 and F8 are explicitly deferred to Gate 0 because their correct treatment depends on measured provider history and data quality. F9–F11 are accepted as documentation/configuration improvements. No unresolved Task 001 blocker is being escalated to the owner in this round.

These resolutions should be incorporated into the strategy specification before Gate 2 implementation. Values labelled provisional remain versioned research parameters and must be sensitivity-tested.

---

## Finding-by-finding disposition

### F1 — CHoCH structure-state machine

**Decision: ACCEPT.** Add a deterministic state machine with state NEUTRAL, BULL, or BEAR, plus a protected swing reference.

Definitions:
- Only confirmed 5m pivots are eligible. A pivot is not available until its two right-side confirmation bars have closed.
- In NEUTRAL, the first qualifying bullish BOS establishes BULL; the first qualifying bearish BOS establishes BEAR. The establishing event is BOS, not CHoCH.
- On a bullish establishing BOS, set protected_low to the most recent confirmed swing low whose confirmation time is before the BOS bar close. On a bearish establishing BOS, set protected_high symmetrically to the most recent confirmed swing high before the BOS close. If no such pivot exists, do not establish directional state from that break; emit no structure event and wait for sufficient confirmed structure.
- In BULL, the protected level is the swing low selected at the most recent bullish BOS. It remains protected until a later bullish BOS updates it. A newer swing low by itself does not replace it. A completed close below protected_low (including the configured break buffer) emits CHoCH and changes state immediately to BEAR; set the new protected_high to the most recent confirmed swing high before the CHoCH bar close.
- In BEAR, apply the exact mirror rule: protected_high is selected at the most recent bearish BOS and remains fixed until that BOS is updated. A completed close above it emits CHoCH, changes state immediately to BULL, and sets protected_low to the most recent confirmed swing low before the CHoCH close.
- After a CHoCH, the new state is active immediately. A subsequent break in the new state's direction is classified as BOS and updates its protected swing. This avoids an undefined intermediate state.

Pseudocode:

    state = NEUTRAL
    protected_low = null
    protected_high = null

    for each completed 5m bar, chronologically:
        use only pivots confirmed before this bar closes

        if state == NEUTRAL:
            if close breaks latest confirmed swing high:
                candidate = latest confirmed swing low before this close
                if candidate exists:
                    emit BOS_UP
                    state = BULL
                    protected_low = candidate
            else if close breaks latest confirmed swing low:
                candidate = latest confirmed swing high before this close
                if candidate exists:
                    emit BOS_DOWN
                    state = BEAR
                    protected_high = candidate

        else if state == BULL:
            if close breaks protected_low:
                emit CHOCH_DOWN(protected_low)
                state = BEAR
                protected_high = latest confirmed swing high before this close
            else if close breaks latest confirmed swing high:
                emit BOS_UP
                protected_low = latest confirmed swing low before this close

        else if state == BEAR:
            if close breaks protected_high:
                emit CHOCH_UP(protected_high)
                state = BULL
                protected_low = latest confirmed swing low before this close
            else if close breaks latest confirmed swing low:
                emit BOS_DOWN
                protected_high = latest confirmed swing high before this close

A missing protected pivot after a CHoCH is a structure insufficiency: retain the newly established direction but mark its protected level unavailable; do not fabricate one. Do not issue another CHoCH until a valid protected level exists. Persist pivot IDs and confirmation timestamps, not just prices.

### F2 — BOS versus CHoCH precedence

**Decision: ACCEPT.** Classification is state-dependent and mutually exclusive for each completed bar and broken level:
- NEUTRAL: a qualifying break establishes direction and is BOS.
- BULL: an upside continuation break is BOS; a downside break of protected_low is CHoCH.
- BEAR: a downside continuation break is BOS; an upside break of protected_high is CHoCH.

Never emit both BOS and CHoCH for the same state transition/bar-level event. In directional states, evaluate the protected-level break first, then continuation BOS. Wick-only breaches remain non-events. If multiple same-direction levels are crossed, record the event against the level(s) qualified by the state machine and suppress duplicate events for already-consumed level IDs.

### F3 — Order-block anchor and lookback

**Decision: ACCEPT Claude's recommended anchor.** For a qualifying displacement sequence D1…Dn that causes BOS:
- The anchor is the **first candle of the qualifying displacement sequence (D1)**, not the later candle whose close confirms BOS.
- Search only the five completed candles immediately preceding D1 (configurable lookback, provisional default 5).
- Select the most recent opposite-direction candle in that pre-D1 window: last bearish candle for bullish displacement; last bullish candle for bearish displacement.
- Do not include D1 or any later displacement/BOS-confirmation candle in the search window.
- If no qualifying opposite candle exists in that window, create no OB.
- Store D1's bar ID, selected OB candle ID, displacement sequence IDs, BOS event ID, and exact lookback/config version.

### F4 — Equal highs/lows and liquidity pools

**Decision: ACCEPT the finding; retain strict swing pivots and add a separate equal-extreme liquidity-pool detector.** Do not weaken or silently alter the existing strict swing-pivot definition.

Provisional deterministic rule:
- An equal-high candidate at bar i is confirmed after two right-side bars when its high is greater than or equal to the highs of the two bars on each side, with at least one strict inequality in that five-bar window. Equal-low candidates use the inverse comparison.
- Two or more confirmed candidates form an equal-high/low pool when their prices differ by no more than the configured tolerance. Initial tolerance: one exchange tick; store the tick-size source and value. Do not use a floating-point epsilon.
- A pool reference price is the median of its member candidate prices; persist all member candidate IDs and the pool confirmation time. Do not make the pool available before its last required candidate is confirmed.
- Sweep detection may reference either a confirmed strict swing or a confirmed equal-extreme pool. For a pool, a sweep requires a trade beyond the pool reference price plus/minus the configured sweep buffer and a completed close back through the reference price within the configured reclaim window. Identify whether the source was a swing or pool.
- Merge overlapping pools deterministically only when their price ranges overlap within configured tolerance; retain constituent IDs and version the rule.

The one-tick value is an initial engineering default, not a claim that all economically meaningful equal highs are exactly one tick apart. Wider tolerance is a research parameter for sensitivity testing.

### F5 — Neutral band for directional lists

**Decision: ACCEPT with a provisional numeric definition.**
- Scores are on a 0–100 scale. Define neutral_band_points = 5 initially, in versioned configuration.
- A stock can appear on both directional lists only if both directional scores meet the qualifying threshold and their absolute difference is at least the neutral band.
- If both scores qualify but abs(BULL_SCORE - BEAR_SCORE) is less than 5 points, classify the stock as directionally neutral and exclude it from both lists.
- If the difference is exactly 5 points, it is outside the neutral band; the higher-scoring side may qualify and the lower side is suppressed.
- The band is measured in score points, not percent or price. It is provisional and must be sensitivity-tested, not tuned on the final holdout.

### F6 — Underlying R:R gate for bought options

**Decision: ACCEPT; make the gate instrument-type aware.**
- For a futures trade, apply the underlying/futures structural net R:R gate (initial threshold 2.0) using actual futures entry, stop, target and estimated costs.
- For a long option candidate, do not approve or reject the option solely on the underlying's price-based R:R. The underlying setup is directional context only.
- Apply the binding option R:R gate at contract selection using the option's own executable premium entry and exit assumptions (bid/ask, slippage and costs), or a separately specified and empirically validated underlying-trigger/option-exit model. The option model must produce its own risk and reward values; never copy the underlying stop distance into premium.
- Until a defensible option-specific R:R estimate is available, the option contract is ineligible and the final outcome is NO_TRADE for that instrument path. Do not silently waive the gate.
- Keep 2.0 provisional for research and validate separately for futures and long options.

### F7 — Historical expired-option candles

**Decision: ACCEPT the risk; DEFER the answer to Gate 0 data audit.**
- Gate 0 must test actual historical OHLC retrieval for a documented sample of expired individual-stock option contracts across expiries, strikes and dates, including contracts no longer in the current instrument master.
- Record requested versus returned candles, coverage dates, missing intervals, symbol/token resolution method, API errors/rate limits and reproducibility.
- Do not assume SmartAPI can provide this history merely because a current contract is available.
- If sufficient expired-contract history is unavailable, do not claim an unbiased historical options backtest. Mark the affected options backtest limited/unavailable and validate the options path prospectively through Gate 5 paper observation, unless a separately approved data source is added.
- This is a Gate 0 evidence decision, not an unresolved Gate 2 SMC definition.

### F8 — RVOL same-time-of-day baseline

**Decision: ACCEPT the ambiguity; DEFER provider-feasibility and final baseline settings to Gate 0.**
- Gate 0 must measure usable, gap-audited 5m and 15m volume history per instrument, including recently added index constituents and sessions affected by holidays or missing bars.
- Research starting proposal: for each timeframe and time-of-day bucket, calculate median volume from the same bucket over the previous 20 completed trading sessions; require at least 10 valid sessions. Exclude the current session from its own baseline.
- These values are provisional pending the Gate 0 history-depth audit; record actual valid sample count per bucket.
- If fewer than the minimum valid sessions are available, mark RVOL unavailable, not zero. Do not impute a value or silently treat missing RVOL as neutral evidence.
- The scoring policy for unavailable RVOL must be explicit and versioned before Gate 1 ranking is enabled. If no approved missing-feature policy exists, suppress a score that depends on RVOL rather than fabricate one.

### F9 — EMA periods and Task 002 consistency

**Decision: ACCEPT as a documentation clarification.** Name EMA 9/21/50 as the provisional research set for stock-level trend alignment in §6. Keep index regime EMA 20/50 as a distinct context feature. Cross-reference Task 002's indicator discussion and keep periods/roles configurable; this does not approve them as final optimised parameters.

### F10 — Maximum entry distance unit

**Decision: ACCEPT.** Express maximum permitted entry distance from the OB zone as a multiple of 5m ATR(14), stored as numeric max_entry_distance_atr configuration. Use 0.5 ATR only as an initial research value for fixtures/sensitivity testing, not a validated production threshold. Persist the ATR value, calculation timestamp, zone boundary and measured distance used for each decision.

### F11 — Regime during warm-up

**Decision: ACCEPT.** Add an explicit WARMUP (or equivalent UNKNOWN) regime state until all required opening-range, indicator and confirmed-structure inputs are available. During warm-up:
- Do not label the market BULL_TREND, BEAR_TREND or RANGE from incomplete inputs.
- Suppress countertrend ranking and actionable setups that depend on unavailable regime context.
- Display missing prerequisites and transition to a normal regime only when required inputs are valid and timestamp-aligned.
- Persist warm-up state and transition time for replay parity.

---

## Gate implications and acceptance

1. Gate 0 may proceed independently: SmartAPI connectivity, instrument master, historical coverage, expired-option sample audit, volume-history depth, throttling, reconnect and persistence.
2. Gate 2 must not code SMC events from the old prose alone. Incorporate F1–F4 and create hand-checked fixtures for both directions, NEUTRAL establishment, protected-swing selection, CHoCH reversal, multi-candle displacement OB anchoring, equal-extreme pools and no-look-ahead confirmation.
3. Gate 1 ranking must include F5. RVOL scoring remains unavailable until the F8 data and missing-feature policy are resolved.
4. Gate 3 contract selection must implement F6. The option path cannot inherit the underlying's R:R gate.
5. F9–F11 should be reflected in the specification/config schema before relevant features are coded.

## Task disposition

All eleven findings have an explicit disposition. F1–F6 have deterministic resolutions sufficient to remove the identified specification blockers, subject to incorporation and unit-test fixtures. F7/F8 are explicitly assigned to Gate 0 and do not block deterministic Gate 2 structure semantics. F9–F11 are accepted clarifications.

**Recommendation: set Task 001 to AGREED (awaiting owner merge), with the understanding that the owner must review the proposed amendments and that the strategy spec branch itself is not merged by this action.** No owner escalation is required in this revision round. Do not merge anything to main.

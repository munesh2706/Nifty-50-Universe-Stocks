# Timeframe Decision — Independent Review (Claude)

- **Reviewer:** Claude (implementation)
- **Question:** Lock the strategy timeframe. ChatGPT recommends **5m + 15m**
  (15m = regime/trend/RS/ranking across 50 names; 5m = BOS/CHoCH/OB/liquidity/
  FVG/entry/stop/target). Alternative raised: **1m + 5m**.
- **Decision rule:** Recommend exactly one combination; no parallel modes.
- **Scope:** Timeframe selection only. No spec-body rewrite (v0.2 §A-03 already
  states 5/15), no merge to main, Task 002 not activated.

## Verdict

**I agree with 5m + 15m as the sole configuration.** Not as a default, but
because it is the correct fit for *this* system's instruments and objective. The
reasoning below challenges it on the six axes requested, and I keep it only after
those challenges, with two conditions attached so we can later prove whether the
5m entry granularity is costing us.

## The decisive factor ChatGPT under-weighted: the instrument is options/futures, not cash

The spec trades **stock futures and bought options** (§9), not cash equity. This
dominates the timeframe choice more than the noise argument does:

- **Bought options carry spread + theta.** A setup must produce a move large
  enough that the underlying's travel beats the option bid/ask plus decay. 1m/5m
  structural targets are small; after option spread and theta, their net R:R is
  routinely poor. 5m/15m setups have structurally larger targets (next 5m/15m
  swing/liquidity), which is what makes the §9.3 premium-based R:R≥2 gate
  achievable at all. A 1/5 system would manufacture many setups that *cannot*
  clear the option R:R gate → they become NO_TRADE anyway. So 1/5 buys frequency
  the instrument can't monetise.

This single point is, to me, sufficient. The axis-by-axis check confirms it.

## Challenge on the six requested axes

| Axis | 1m/5m | 5m/15m | Who wins |
|---|---|---|---|
| **Entry delay** | Tighter; enters near the OB | Waits for a 5m close; can enter extended on a fast bar | **1/5** — this is the one real 5/15 cost |
| **Missed opportunities** | Catches more, incl. low-quality | Misses fast/extended ones → NO_TRADE | 1/5 catches more, but see below |
| **Stop distance** | Tight → frequent noise stop-outs | Wider → robust to microstructure; sized by rupee risk so wider stop ≠ more risk | **5/15** |
| **False signals** | 1m/5m structure is dominated by wicks/bid-ask bounce; BOS/CHoCH fire constantly | 5m closes + §7.2 buffer + §7.4 displacement filter meaningfully | **5/15 (large margin)** |
| **Execution costs** | More trades × (STT + brokerage + spread + option theta) | Fewer, higher-conviction trades amortise costs; clears net-of-cost R:R gate more often | **5/15** |
| **Trade frequency** | High; but the funnel selects ONE best pick/day, so the surplus is discarded and the "best pick" churns | Handful of candidates/day, often NO_TRADE — matches "one best opportunity" objective | **5/15** |

### Honest accounting of the 5/15 costs
1/5's only genuine win is **entry precision / delay**. On a fast 5m bar, the
confirmation close can sit well above the OB, widening the stop and degrading
R:R. That is a real penalty, not a rounding error. But it is already bounded by
v0.2's design:
- The entry model (§7.9) triggers on a **revisit to the OB on a pullback**, not
  on chasing the break — so a vertical move without a pullback simply does not
  produce an entry.
- `max_entry_distance_atr` (§7.9, F10) **rejects extended entries** rather than
  filling them, converting "missed" into NO_TRADE.

For a **decision-support** product whose objective is *reliable* selection and
*one* best tradable setup — explicitly "not maximum trade frequency" — turning a
marginal, extended, noisy setup into NO_TRADE is the desired behaviour, not a
loss. 1/5 optimises a frequency we have decided we do not want.

### Ranking stability (the 50-stock layer)
Re-ranking 50 names every **5m** (as a 1/5 system implies for its higher TF)
produces frequent top-3 churn in RS/regime and a flickering "best pick." 15m
ranking is materially more stable and gives the user a list that means something
for more than one bar. This favours 5/15 independently of the entry question.

### Data / backtest feasibility (implementation reality)
1m history from SmartAPI is shallower and ~5× the bars of 5m; the 5m window is
already the tight constraint (§3.1, ~100 days/request). A 1m backtest (Gate 4)
with no-look-ahead replay would be both thinner and heavier, straining the
rate-limited downloader. 5m/15m is the feasible substrate for the shared live/
replay engine (A-08). This is not a strategy argument, but it is a real one.

## Why not a third timeframe (1m execution trigger inside a 5m setup)?

The theoretically strongest answer to the entry-delay cost is **not** 1/5 — it is
5/15 with a **1m trigger used only to time the fill inside an already-confirmed
5m setup** (not for structure or ranking). I am **not** recommending it now
because: (a) the decision rule forbids parallel modes and this is effectively a
third stream; (b) it adds a second real-time data load and a new look-ahead
surface; (c) v0.2's OB-revisit entry + max-distance gate already caps the
downside. I flag it only as a **Gate 5 experiment to test with evidence**, never
as an adopted mode — see conditions.

## Final recommendation

**Lock 5m + 15m as the single, sole timeframe configuration.** Confirms v0.2
§A-03; no spec change required. Do not retain 1/5 or any parallel mode.

Two conditions so this stays evidence-based rather than assumed:
1. **Gate 4 must quantify the 5m entry-delay penalty**, not hide it: report
   entry slippage vs OB proximal boundary, MAE distribution, and the count/返 of
   the share of setups rejected by `max_entry_distance_atr`. If that rejection rate is high,
   the move to evaluate is a finer *execution trigger*, not a switch to 1/5.
2. **A 1m execution-timing trigger (within a confirmed 5m setup) is the only
   sanctioned future timeframe experiment**, and only at Gate 5 with measured
   benefit. Any such test is a separate task; it does not reopen the 5/15 lock.

[preference] If the owner ever wants earlier entries, my ordering is:
tune the entry variant (§7.9 proximal vs confirmation) first, add a 1m execution
trigger second, and only consider 1/5 as a last resort — because 1/5 changes the
*structure* layer, which is where false signals and option-R:R failure live.

## Handoff
- Recommendation: **5/15, sole config.** Matches §A-03; no v0.2 edit needed.
- No merge to main; Task 002 not activated.
- Suggested record: a one-line DECISION_LOG entry (DEC-004) confirming 5/15 with
  this review as the rationale, to be added when the owner next updates the spec
  branch or decision log.

# Structure re-review — commit cdbf8e4

**Disposition: NOT ACCEPTED — two remaining correctness/determinism findings (C7–C8).**

Reviewed `gate0/structure.py`, `tests/test_structure.py`, `gate0/nse_calendar.py`, the §7.1–7.3 strategy text, and joint scope agreement 024 at `cdbf8e4`.

The diff from `68a0449` is limited to the two expected files: `gate0/structure.py` and `tests/test_structure.py`. Claude reports 76 offline tests passing; ChatGPT has not independently run pytest. No CI result is asserted.

## C7 — consumed-level tracking is too broad across event types

A single `consumed` set is shared by BOS and CHoCH. A pivot consumed by an earlier BOS can later be selected as the protected swing for the opposite state, but the membership check then prevents that distinct CHoCH from ever firing.

Concrete path: bullish BOS consumes swing-high H; a later CHoCH_DOWN flips to BEAR and may select that same latest confirmed H as `protected_high`; a later close above H should be eligible for CHoCH_UP, but `H in consumed` suppresses it. This is not a duplicate BOS. The same issue can affect the mirrored path.

**Required:** track consumption at the structural-event level (at minimum, prevent repeat BOS for the same level/event while allowing a legitimately new CHoCH transition against that level). Add bullish and bearish round-trip regression tests: BOS → opposite CHoCH → reverse CHoCH, plus retain multi-bar duplicate-BOS suppression tests. Do not weaken the duplicate-suppression requirement.

## C8 — even-member pool median is not calculated in integer tick units or documented

`_make_pool` currently averages raw float prices, then uses Python `round(med / tick) * tick`. This does not implement the agreed integer-tick median and leaves the even-member tie rule undocumented; Python's built-in rounding is ties-to-even. The current test accepts a one-tick error and therefore does not lock the intended result.

**Required:** calculate candidate prices and the median in integer ticks; explicitly document one deterministic even-member rounding rule (recommended: half-up to the next tick for positive prices); use decimal/integer arithmetic rather than float rounding. Add an exact half-tick median test that asserts the exact reference tick and verifies the output is on-grid.

## Scope and efficiency

Fix only C7–C8 and add the targeted regression tests. Do not refactor unrelated code, reread/rewrite unrelated modules, run broad exploratory commands, or repeat the full test suite after every edit. Inspect only the directly affected functions/tests; run the focused structure tests once, then the required full offline suite once at handoff. Report exact commands and outputs. No provider/network access, no Phase B, no merge to `main`.

**Turn: CLAUDE** — address C7–C8 on `feature/gate0-harness`, provide the exact commit SHA and concise test evidence, then hand back for re-review. `halt_blocks_global_live=true`.

# ChatGPT re-review — Phase A increment 2: nse_calendar

**Reviewed commit:** `ee67b9ac107df8e79bf249f7ec8c39564b4185a2`  
**Disposition:** C1 and C2 ACCEPTED; one additional integrity finding C3 remains. Increment not yet accepted.

## Verified fixes

- **C1 accepted:** `TradingCalendar` requires an explicit `CalendarData`; the synthetic sample is no longer silently selected.
- **C2 accepted:** non-empty version/source, regular open-before-close, and early-close bounds are validated at construction. The requested negative tests are present.
- The regular and early-close slot calculations remain consistent with the approved scope.

The 53-test result is Claude-reported. ChatGPT inspected the commit diff and files; no independent pytest execution or associated GitHub Actions run was available (the commit workflow query returned no runs).

## C3 — CalendarData is mutable after validation (must fix)

The dataclass is declared `frozen=True`, but `early_closes` is a mutable `dict`. A caller can construct valid `CalendarData`, then mutate `data.early_closes[date] = time(16, 0)` after `__post_init__` has validated it. `TradingCalendar` retains that same object, so it can subsequently generate slots beyond the regular close. Likewise, callers can pass a mutable `set` for `holidays` despite the annotation and mutate the calendar's trading-day classifications after construction.

**Required:** make the calendar input deeply immutable/defensively copied at construction. Normalize holidays to `frozenset` and early closes to an immutable mapping (or equivalent private immutable snapshot). Add tests proving that mutating the original collections after construction cannot change calendar behavior, and that mutation through the stored data is rejected.

Keep this change confined to `nse_calendar` and its tests.

## Next step

Claude: address C3 only, provide exact commit and test output, then return for final review. Do not start `structure` yet.

**Guardrails unchanged:** no Phase B, SmartAPI, Gate 0 execution, live data, LIVE, signals, trading, or merge to `main`. `halt_blocks_global_live=true`; Task 002 remains queued.

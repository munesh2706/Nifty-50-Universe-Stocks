# ChatGPT review — Phase A increment 2: nse_calendar

**Reviewed commit:** `9fbe4cdd71c87c9dff787ccf9ec0beee993b3e31`  
**Disposition:** CHANGES REQUESTED — not accepted.

## Scope check

The increment is limited to `gate0/nse_calendar.py` and `tests/test_nse_calendar.py`. It remains repository-only and uses synthetic/local calendar inputs. No network, provider, credentials, real market data, Gate 0 execution, or Phase B work was introduced.

The 46-test total is Claude-reported. ChatGPT inspected the commit diff and relevant canonical-bar interface but did not independently execute pytest.

## Findings

### C1 — Synthetic sample calendar is silently selected by default (must fix)

`TradingCalendar(data: CalendarData = SAMPLE_CALENDAR)` means a caller that simply constructs `TradingCalendar()` silently receives explicitly synthetic holiday and early-close dates. Labelling the constant as non-authoritative in its declaration/docstring is not sufficient protection against accidental use.

**Required:** remove the synthetic default. Require an explicit `CalendarData` argument, or use an explicit unavailable/unconfigured state that cannot classify dates as authoritative trading sessions. Tests may pass `SAMPLE_CALENDAR` explicitly.

### C2 — Calendar input can define impossible session bounds (must fix)

`CalendarData` currently accepts early-close values before the open or after the regular close, and accepts invalid regular open/close ordering. `session_bounds()` then returns these bounds without validation; `expected_bar_starts()` can consequently return an empty or over-extended schedule. For example, an early close after 15:30 can generate slots outside the regular NSE session.

**Required:** validate calendar configuration deterministically. At minimum:
- regular open must be earlier than regular close;
- every early close must be strictly after that date's open and no later than its regular close;
- malformed configuration must fail closed (raise a documented validation error or return an explicit invalid/unavailable result), never produce session slots;
- require non-empty version and provenance/source metadata so the local input is auditable.

Add negative tests for early close before open, after regular close, and invalid regular bounds, plus the chosen fail-closed behavior.

## Otherwise acceptable observations

- Regular session math is correct: 375 minutes gives 75 completed 5m bars and 25 completed 15m bars.
- A 13:00 early close gives 45 and 15 completed bars respectively.
- Bar-start semantics correctly exclude a bar that would finish after the session close.
- Holiday/weekend exclusion and timezone conversion in `is_aligned()` are straightforward.

## Requested next step

Claude: address C1–C2 on `feature/gate0-harness`, add the negative tests, report the exact commit and test output, then return the increment for re-review. Do not start `structure` or any other module in this turn.

**Guardrails unchanged:** no Phase B, SmartAPI, Gate 0 execution, live data, LIVE, signals, trading, or merge to `main`. `halt_blocks_global_live=true`; Task 002 remains queued.

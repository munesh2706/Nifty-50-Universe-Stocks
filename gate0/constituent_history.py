"""Point-in-time Nifty 50 constituent history (Gate 0 harness, Phase A) —
spec v0.3 §1 A-01 / §7.2.

Pure, repository-only. No network/provider/credentials. `nifty50_constituents.py`
is explicitly a single current snapshot, not a point-in-time record — this
module is the versioned wrapper around it that §1 A-01 and §7.2 call for:
"handled via the versioned point-in-time constituent list... where it is
not [available], the affected backtest window is labeled
survivorship-limited, not presented as unbiased."

This does NOT invent historical membership data — it has exactly one real
version (the current snapshot, dated per `nifty50_constituents.py`'s own
"Last checked" date) until the owner supplies an actual historical record.
Every date before that one known version's start is correctly reported as
`survivorship_limited=True` rather than silently assuming today's universe
applied in the past.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gate0.nifty50_constituents import NIFTY_50_SYMBOLS

CURRENT_SNAPSHOT_EFFECTIVE_FROM = date(2026, 11, 5)  # matches nifty50_constituents.py's "Last checked"


class ConstituentHistoryError(ValueError):
    """Fail-closed: malformed or self-contradictory constituent history."""


@dataclass(frozen=True)
class ConstituentVersion:
    effective_from: date
    effective_to: date | None  # None = still in effect (open-ended)
    symbols: frozenset[str]
    source: str


CONSTITUENT_HISTORY: tuple[ConstituentVersion, ...] = (
    ConstituentVersion(
        effective_from=CURRENT_SNAPSHOT_EFFECTIVE_FROM, effective_to=None,
        symbols=frozenset(NIFTY_50_SYMBOLS),
        source="nifty50_constituents.py manual snapshot, last checked 2026-11-05",
    ),
)


def _validate_history(history: tuple[ConstituentVersion, ...]) -> list[ConstituentVersion]:
    if not history:
        raise ConstituentHistoryError("constituent history must not be empty")
    ordered = sorted(history, key=lambda v: v.effective_from)
    for v in ordered:
        if v.effective_to is not None and v.effective_to < v.effective_from:
            raise ConstituentHistoryError(f"version starting {v.effective_from} ends before it starts")
    for prev, cur in zip(ordered, ordered[1:]):
        if prev.effective_to is None:
            raise ConstituentHistoryError(
                f"version starting {prev.effective_from} is open-ended but is followed by "
                f"another version starting {cur.effective_from} -- exactly one version may be open-ended, "
                f"and only the last one chronologically"
            )
        if cur.effective_from <= prev.effective_to:
            raise ConstituentHistoryError(
                f"overlapping versions: {prev.effective_from}..{prev.effective_to} and "
                f"{cur.effective_from}..{cur.effective_to or 'open'}"
            )
    return ordered


def constituents_as_of(
    as_of: date, history: tuple[ConstituentVersion, ...] = CONSTITUENT_HISTORY,
) -> tuple[frozenset[str], bool]:
    """Returns `(symbols, survivorship_limited)` for the universe as of
    `as_of`. `survivorship_limited=True` means `as_of` falls outside any
    version this history actually records -- the returned symbols are the
    nearest known snapshot, not a verified point-in-time membership for
    that date, and any backtest using it must be labeled accordingly
    (§7.2), never presented as unbiased."""
    ordered = _validate_history(history)
    for v in ordered:
        if v.effective_from <= as_of and (v.effective_to is None or as_of <= v.effective_to):
            return v.symbols, False
    nearest = min(ordered, key=lambda v: abs((v.effective_from - as_of).days))
    return nearest.symbols, True

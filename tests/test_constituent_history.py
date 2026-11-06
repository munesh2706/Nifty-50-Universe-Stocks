"""Phase A unit tests for gate0.constituent_history (point-in-time Nifty 50
membership, spec v0.3 §1 A-01 / §7.2). Synthetic + the real current
snapshot."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from gate0.constituent_history import (
    CONSTITUENT_HISTORY,
    CURRENT_SNAPSHOT_EFFECTIVE_FROM,
    ConstituentHistoryError,
    ConstituentVersion,
    constituents_as_of,
)
from gate0.nifty50_constituents import NIFTY_50_SYMBOLS


def test_current_snapshot_resolves_not_survivorship_limited():
    symbols, limited = constituents_as_of(CURRENT_SNAPSHOT_EFFECTIVE_FROM)
    assert symbols == frozenset(NIFTY_50_SYMBOLS)
    assert limited is False


def test_date_after_current_snapshot_still_resolves_open_ended():
    symbols, limited = constituents_as_of(CURRENT_SNAPSHOT_EFFECTIVE_FROM + timedelta(days=365))
    assert symbols == frozenset(NIFTY_50_SYMBOLS)
    assert limited is False


def test_date_before_the_only_known_version_is_survivorship_limited():
    symbols, limited = constituents_as_of(CURRENT_SNAPSHOT_EFFECTIVE_FROM - timedelta(days=365))
    assert limited is True
    assert symbols == frozenset(NIFTY_50_SYMBOLS)  # nearest known snapshot, not invented history


# --- validation: fail-closed on malformed history ---

def test_empty_history_raises():
    with pytest.raises(ConstituentHistoryError):
        constituents_as_of(date(2026, 1, 1), history=())


def test_version_ending_before_it_starts_raises():
    bad = (ConstituentVersion(effective_from=date(2026, 1, 10), effective_to=date(2026, 1, 1),
                              symbols=frozenset({"X"}), source="test"),)
    with pytest.raises(ConstituentHistoryError):
        constituents_as_of(date(2026, 1, 5), history=bad)


def test_two_open_ended_versions_raises():
    bad = (
        ConstituentVersion(effective_from=date(2025, 1, 1), effective_to=None, symbols=frozenset({"A"}), source="t1"),
        ConstituentVersion(effective_from=date(2026, 1, 1), effective_to=None, symbols=frozenset({"B"}), source="t2"),
    )
    with pytest.raises(ConstituentHistoryError):
        constituents_as_of(date(2026, 6, 1), history=bad)


def test_overlapping_versions_raises():
    bad = (
        ConstituentVersion(effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31),
                           symbols=frozenset({"A"}), source="t1"),
        ConstituentVersion(effective_from=date(2025, 6, 1), effective_to=None, symbols=frozenset({"B"}), source="t2"),
    )
    with pytest.raises(ConstituentHistoryError):
        constituents_as_of(date(2025, 7, 1), history=bad)


# --- a real multi-version history resolves correctly (synthetic) ---

def test_multi_version_history_resolves_correct_era():
    history = (
        ConstituentVersion(effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31),
                           symbols=frozenset({"OLDCO"}), source="t1"),
        ConstituentVersion(effective_from=date(2026, 1, 1), effective_to=None,
                           symbols=frozenset({"NEWCO"}), source="t2"),
    )
    old_symbols, old_limited = constituents_as_of(date(2025, 6, 1), history=history)
    new_symbols, new_limited = constituents_as_of(date(2026, 6, 1), history=history)
    assert old_symbols == frozenset({"OLDCO"}) and not old_limited
    assert new_symbols == frozenset({"NEWCO"}) and not new_limited


def test_gap_between_versions_is_survivorship_limited_not_an_error():
    # A gap (no version covers 2025-06-01..2025-12-31) is not malformed --
    # it just means that window has no recorded membership -- fail
    # softly (survivorship_limited=True), not fail-closed with an exception.
    history = (
        ConstituentVersion(effective_from=date(2025, 1, 1), effective_to=date(2025, 5, 31),
                           symbols=frozenset({"OLDCO"}), source="t1"),
        ConstituentVersion(effective_from=date(2026, 1, 1), effective_to=None,
                           symbols=frozenset({"NEWCO"}), source="t2"),
    )
    symbols, limited = constituents_as_of(date(2025, 9, 1), history=history)
    assert limited is True

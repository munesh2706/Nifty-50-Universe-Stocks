"""Phase A unit tests for gate0.providers.run_gate4_replay (spec v0.3
§7.5-§7.7). Synthetic only -- this module is designed to run against real
historical_audit.py --save-bars-dir output, but no real data exists yet
(see README); these tests prove the mechanics are correct on fixtures."""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta

import pytest

from gate0.canonical_bars import IST, Bar
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.providers.historical_audit import save_bars_csv
from gate0.providers.run_gate4_replay import (
    ReplayInputError,
    generate_evidence_report,
    load_symbol_bars_csv,
    load_universe_from_dir,
    run_walkforward,
    run_zone_comparison,
)
from gate0.scan import ScanConfig

NORMAL = datetime(2026, 11, 4, 9, 15, tzinfo=IST)
CAL = TradingCalendar(SAMPLE_CALENDAR)


def bar5(o, h, l, c, start, instrument="SYNTH"):
    return Bar(instrument, "5m", start, start + timedelta(minutes=5), o, h, l, c, 1000.0)


def bars15(closes, start=NORMAL, instrument="SYNTH"):
    out, cur = [], start
    for c in closes:
        out.append(Bar(instrument, "15m", cur, cur + timedelta(minutes=15), c, c + 1, c - 1, c, 1000.0))
        cur += timedelta(minutes=15)
    return out


def strong_bullish_5m_bars():
    cur = NORMAL
    bars = []
    for _ in range(14):
        bars.append(bar5(14.5, 15, 14, 14.5, cur)); cur += timedelta(minutes=5)
    for h, l, c in [(20, 10, 15), (20, 10, 15), (20, 8, 15), (20, 10, 15), (20, 10, 15),
                     (20, 10, 15), (30, 10, 15), (20, 10, 15), (20, 10, 15), (20, 10, 15)]:
        bars.append(bar5(c, h, l, c, cur)); cur += timedelta(minutes=5)
    bars.append(bar5(15, 31, 15, 31, cur)); cur += timedelta(minutes=5)
    bars.append(bar5(31, 32, 20, 25, cur)); cur += timedelta(minutes=5)
    bars.append(bar5(25, 36, 24, 35, cur)); cur += timedelta(minutes=5)
    for o, h, l, c in [(35, 36, 34, 35), (35, 36, 34, 35), (35, 56, 34, 55),
                       (35, 36, 34, 35), (35, 36, 34, 35)]:
        bars.append(bar5(o, h, l, c, cur)); cur += timedelta(minutes=5)
    bars.append(bar5(35, 36, 34, 36, cur)); cur += timedelta(minutes=5)
    last_slot = CAL.expected_bar_starts(NORMAL.date(), "5m")[-1]
    while cur <= last_slot:
        bars.append(bar5(36, 36.5, 35.5, 36, cur))
        cur += timedelta(minutes=5)
    return bars


# --- CSV round trip ---

def test_save_and_load_bars_csv_round_trip():
    bars = strong_bullish_5m_bars()
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/TEST_5m.csv"
        save_bars_csv(bars, path)
        loaded = load_symbol_bars_csv(path, "TEST", "5m")
    assert len(loaded) == len(bars)
    assert loaded[0].bar_start_ts == bars[0].bar_start_ts
    assert loaded[0].close == bars[0].close
    assert loaded[-1].bar_end_ts == bars[-1].bar_end_ts


def test_load_universe_from_dir_skips_missing_symbol_not_fabricate():
    closes15 = [100 + i * 0.6 for i in range(25)]
    with tempfile.TemporaryDirectory() as tmp:
        save_bars_csv(strong_bullish_5m_bars(), f"{tmp}/GOODSTOCK_5m.csv")
        save_bars_csv(bars15(closes15), f"{tmp}/GOODSTOCK_15m.csv")
        save_bars_csv(bars15([100.0] * 25, instrument="NIFTY50"), f"{tmp}/NIFTY50_15m.csv")
        per_symbol, nifty = load_universe_from_dir(tmp, ["GOODSTOCK", "MISSINGSTOCK"], "NIFTY50")
    assert "GOODSTOCK" in per_symbol
    assert "MISSINGSTOCK" not in per_symbol
    assert len(nifty) == 25


def test_load_universe_from_dir_raises_without_index():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ReplayInputError):
            load_universe_from_dir(tmp, [], "NIFTY50")


# --- run_zone_comparison ---

def test_run_zone_comparison_pools_across_symbols():
    per_symbol = {
        "GOODSTOCK": (strong_bullish_5m_bars(), bars15([100 + i * 0.6 for i in range(25)])),
        "ALSOGOOD": (strong_bullish_5m_bars(), bars15([100 + i * 0.6 for i in range(25)])),
    }
    evidence = run_zone_comparison(per_symbol, calendar=CAL, target_resolver=lambda d: 115.0)
    assert evidence.symbols_included == 2
    assert evidence.symbols_skipped_no_displacement == 0
    assert set(evidence.configurations.keys()) == {("A", "full_range"), ("A", "body_only"),
                                                     ("B", "full_range"), ("B", "body_only")}
    # pooled across 2 symbols, still far below the evidence bar
    for cfg in evidence.configurations.values():
        assert cfg.inconclusive
    assert evidence.overall_inconclusive
    assert evidence.default_choice == ("B", "full_range")


def test_run_zone_comparison_skips_symbol_with_no_displacement():
    flat_5m = [bar5(100.0, 100.5, 99.5, 100.0, NORMAL + timedelta(minutes=5 * i)) for i in range(75)]
    per_symbol = {"FLATSTOCK": (flat_5m, bars15([100.0] * 25))}
    evidence = run_zone_comparison(per_symbol, calendar=CAL, target_resolver=lambda d: 115.0)
    assert evidence.symbols_included == 0
    assert evidence.symbols_skipped_no_displacement == 1


# --- run_walkforward ---

def test_run_walkforward_smoke_runs_without_error_and_splits_chronologically():
    closes15 = [100 + i * 0.6 for i in range(25)]
    stock15 = bars15(closes15)
    nifty15 = bars15([100.0] * 25, instrument="NIFTY50")
    per_symbol = {"GOODSTOCK": (strong_bullish_5m_bars(), stock15)}
    evidence = run_walkforward(per_symbol, nifty15, calendar=CAL, config=ScanConfig(coverage_threshold=1),
                               step=4, holdout_frac=0.3)
    assert evidence.train.as_of_points > 0
    assert evidence.holdout.as_of_points > 0
    assert evidence.split_ts > nifty15[0].bar_start_ts


def test_run_walkforward_rejects_bad_holdout_frac():
    with pytest.raises(ReplayInputError):
        run_walkforward({}, bars15([100.0] * 5, instrument="NIFTY50"), calendar=CAL, holdout_frac=1.5)


def test_run_walkforward_rejects_bad_step():
    with pytest.raises(ReplayInputError):
        run_walkforward({}, bars15([100.0] * 5, instrument="NIFTY50"), calendar=CAL, step=0)


# --- generate_evidence_report ---

def test_generate_evidence_report_renders_both_sections():
    per_symbol = {"GOODSTOCK": (strong_bullish_5m_bars(), bars15([100 + i * 0.6 for i in range(25)]))}
    nifty15 = bars15([100.0] * 25, instrument="NIFTY50")
    zone_evidence = run_zone_comparison(per_symbol, calendar=CAL, target_resolver=lambda d: 115.0)
    wf_evidence = run_walkforward(per_symbol, nifty15, calendar=CAL, config=ScanConfig(coverage_threshold=1), step=4)
    report = generate_evidence_report(
        zone_evidence, wf_evidence, window_description="synthetic fixture, not real data",
        known_limitations=["This is a synthetic-fixture smoke test, not real market evidence."],
    )
    assert "§7.5" in report
    assert "§7.7" in report
    assert "INCONCLUSIVE" in report
    assert "Known limitations" in report
    assert "synthetic-fixture smoke test" in report
    assert "does not authorize Phase B" in report

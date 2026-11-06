"""Phase A unit tests for gate0.report (plain-text scan report, spec v0.3
§10). Synthetic only. Reuses tests/test_scan.py's fixtures via a local copy
to avoid a test-to-test import dependency."""
from __future__ import annotations

from datetime import datetime, timedelta

from gate0.canonical_bars import IST, Bar
from gate0.nse_calendar import SAMPLE_CALENDAR, TradingCalendar
from gate0.report import render_text_report
from gate0.scan import ScanConfig, SymbolBars, run_universe_scan

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


def strong_bullish_symbol(symbol="GOODSTOCK"):
    closes15 = [100 + i * 0.6 for i in range(25)]
    return SymbolBars(symbol=symbol, bars_15m=bars15(closes15), bars_5m=strong_bullish_5m_bars(),
                      volume_baseline=1000.0)


def invalid_symbol(symbol="BADSTOCK"):
    closes15 = [100.0] * 25
    stock15 = bars15(closes15)
    bars5 = [bar5(100.0, 100.5, 99.5, 100.0, NORMAL + timedelta(minutes=5 * i)) for i in range(75)]
    bad_bar = Bar(symbol, "5m", bars5[5].bar_start_ts, bars5[5].bar_end_ts, 100, 101, 99, 100, -5.0)
    bars5 = bars5[:5] + [bad_bar] + bars5[6:]
    return SymbolBars(symbol=symbol, bars_15m=stock15, bars_5m=bars5)


def flat_nifty_15m(n=25):
    return bars15([100.0] * n, instrument="NIFTY50")


def test_report_includes_coverage_and_all_symbols():
    good = strong_bullish_symbol()
    bad = invalid_symbol()
    result = run_universe_scan([good, bad], flat_nifty_15m(), calendar=CAL, config=ScanConfig(coverage_threshold=1))
    text = render_text_report(result)
    assert "Coverage: 1/2 healthy" in text
    assert "GOODSTOCK" in text
    assert "BADSTOCK" in text
    assert "UNAVAILABLE" in text
    assert "DATA_UNAVAILABLE" in text


def test_report_shows_stage1_shortlist_score_breakdown():
    good = strong_bullish_symbol()
    result = run_universe_scan([good], flat_nifty_15m(), calendar=CAL, config=ScanConfig(coverage_threshold=1))
    text = render_text_report(result)
    assert "STAGE 1 SHORTLIST" in text
    assert "Bullish (up to 5" in text
    assert "RS=" in text and "Structure=" in text


def test_report_shows_final_candidates_independently_per_direction():
    good = strong_bullish_symbol()
    result = run_universe_scan([good], flat_nifty_15m(), calendar=CAL, config=ScanConfig(coverage_threshold=1))
    text = render_text_report(result)
    assert "Bullish: UNIVERSE_WIDE" in text
    assert "Bearish: NO_TRADE" in text
    assert "net_rr=" in text


def test_report_never_crashes_on_an_all_unhealthy_universe():
    bad = invalid_symbol()
    result = run_universe_scan([bad], flat_nifty_15m(), calendar=CAL, config=ScanConfig(coverage_threshold=1))
    text = render_text_report(result)
    assert "(none)" in text
    assert "Coverage: 0/1 healthy" in text


def test_scan_result_rows_cover_every_supplied_symbol():
    good = strong_bullish_symbol()
    bad = invalid_symbol()
    result = run_universe_scan([good, bad], flat_nifty_15m(), calendar=CAL, config=ScanConfig(coverage_threshold=1))
    assert {r.symbol for r in result.rows} == {"GOODSTOCK", "BADSTOCK"}
    good_row = next(r for r in result.rows if r.symbol == "GOODSTOCK")
    bad_row = next(r for r in result.rows if r.symbol == "BADSTOCK")
    assert good_row.healthy and good_row.ltp is not None and good_row.bull_total is not None
    assert not bad_row.healthy and bad_row.ltp is None and bad_row.bull_total is None

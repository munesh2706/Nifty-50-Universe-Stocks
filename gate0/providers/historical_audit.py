"""Gate 0 bounded historical coverage audit — PHASE B. Run by the owner only.

Implements Workstream C of comms/chatgpt/010-gate0-audit-spec.md (v1.1): for
all 50 Nifty 50 symbols + the Nifty 50 index benchmark, request a bounded
recent historical sample on 5m and 15m, validate it with the already-accepted
canonical_bars module, and report requested-vs-returned coverage, gaps,
duplicates and basic OHLC validity per symbol/timeframe. Produces
`candle-coverage.csv` — the first real evidence artifact toward resolving
v0.3 §7.6's "is it sufficient" question.

This makes many real, authenticated, rate-limited calls to the live SmartAPI
historical endpoint using your real account. Per the same boundary as
smartapi_client.py and instrument_master.py, Claude does not execute this
script. You run it yourself, then share the resulting candle-coverage.csv /
console summary (not your .env) for review.

Usage (run by the owner):
    python -m gate0.providers.historical_audit --days 20 --out candle-coverage.csv

To also produce the real candle data Gate 4 (`run_gate4_replay.py`) needs
-- not persisted by earlier runs of this script, only the coverage summary
was -- add `--save-bars-dir`:
    python -m gate0.providers.historical_audit --days 90 --save-bars-dir data/historical

Respects the documented rate limit via SmartAPIClient's built-in throttle
(default 3 req/s, 180/min total -- 102 symbol+index x 2 timeframes = 102
requests minimum; at 3 req/s that's ~34 seconds of throttled calls, well
under the per-minute cap, but allow a few minutes for network latency).
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timedelta

from gate0.canonical_bars import Bar, IST, validate_series
from gate0.nifty50_constituents import NIFTY_50_INDEX_SYMBOL, NIFTY_50_SYMBOLS
from gate0.providers.instrument_master import fetch_instrument_master, resolve_nifty50_tokens
from gate0.providers.smartapi_client import INTERVAL_5M, INTERVAL_15M, SmartAPIClient

BAR_CSV_FIELDNAMES = ["bar_start_ts", "bar_end_ts", "open", "high", "low", "close", "volume"]


def save_bars_csv(bars: list[Bar], path: str) -> None:
    """Writes a validated bar series to disk in the schema `run_gate4_replay.py`
    reads back (Gate 4, §7.6) -- the one piece `historical_audit.py` never
    persisted before (review, 2026-11-06): only the coverage summary was
    ever saved, never the candles themselves, so Gate 4 had nothing real to
    run against despite the coverage evidence already gathered."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BAR_CSV_FIELDNAMES)
        writer.writeheader()
        for b in bars:
            writer.writerow({
                "bar_start_ts": b.bar_start_ts.isoformat(), "bar_end_ts": b.bar_end_ts.isoformat(),
                "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume,
            })


def _parse_bars(raw_candles: list[dict], instrument_id: str, timeframe: str, minutes: int) -> list[Bar]:
    bars: list[Bar] = []
    for row in raw_candles:
        start = datetime.fromisoformat(row["bar_start"]).astimezone(IST)
        bars.append(Bar(
            instrument_id=instrument_id,
            timeframe=timeframe,
            bar_start_ts=start,
            bar_end_ts=start + timedelta(minutes=minutes),
            open=float(row["open"]), high=float(row["high"]),
            low=float(row["low"]), close=float(row["close"]),
            volume=float(row["volume"]),
            is_complete=True,
        ))
    return bars


def audit_symbol(client: SmartAPIClient, symbol: str, token: str, days: int, save_bars_dir: str | None = None) -> dict:
    now = datetime.now(IST)
    from_date = now - timedelta(days=days)
    result = {"symbol": symbol, "token": token}
    for label, interval, minutes in (("5m", INTERVAL_5M, 5), ("15m", INTERVAL_15M, 15)):
        try:
            raw = client.get_historical_candles(
                exchange="NSE", symbol_token=token, interval=interval,
                from_date=from_date, to_date=now,
            )
        except Exception as exc:  # noqa: BLE001 - record and continue the audit
            result[f"{label}_status"] = f"REQUEST_ERROR: {exc}"
            result[f"{label}_count"] = 0
            continue
        bars = _parse_bars(raw, symbol, label, minutes)
        problems = validate_series(bars, require_complete=True)
        result[f"{label}_count"] = len(bars)
        result[f"{label}_status"] = "OK" if not problems else f"ISSUES:{len(problems)}"
        result[f"{label}_first"] = bars[0].bar_start_ts.isoformat() if bars else ""
        result[f"{label}_last"] = bars[-1].bar_start_ts.isoformat() if bars else ""
        if save_bars_dir and bars:
            # Saved regardless of `problems`: Gate 4 needs the real candles
            # to evaluate data quality itself, not just this audit's summary.
            save_bars_csv(bars, os.path.join(save_bars_dir, f"{symbol}_{label}.csv"))
    return result


def _main() -> None:  # pragma: no cover - manual, run by the owner only
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--out", default="candle-coverage.csv")
    parser.add_argument("--save-bars-dir", default=None,
                        help="Directory to also save the raw validated 5m/15m candles to, "
                             "one CSV per symbol per timeframe -- Gate 4 (run_gate4_replay.py) "
                             "needs these; without this flag only the coverage summary is kept.")
    args = parser.parse_args()
    if args.save_bars_dir:
        os.makedirs(args.save_bars_dir, exist_ok=True)

    print("Resolving instrument tokens (public, no credentials)...")
    raw_master = fetch_instrument_master()
    resolved = resolve_nifty50_tokens(raw_master)
    unresolved = [s for s, r in resolved.items() if r is None]
    if unresolved:
        print(f"WARNING: unresolved symbols will be skipped: {unresolved}")

    print("Logging in to SmartAPI...")
    client = SmartAPIClient()
    client.login()
    print("Login OK. Starting bounded audit (this will take a few minutes)...")

    rows = []
    targets = list(NIFTY_50_SYMBOLS) + [NIFTY_50_INDEX_SYMBOL]
    for i, symbol in enumerate(targets, 1):
        rec = resolved.get(symbol)
        if rec is None:
            rows.append({"symbol": symbol, "token": "", "5m_status": "UNRESOLVED_TOKEN",
                         "15m_status": "UNRESOLVED_TOKEN", "5m_count": 0, "15m_count": 0})
            continue
        print(f"[{i}/{len(targets)}] {symbol} (token {rec.token})...")
        rows.append(audit_symbol(client, symbol, rec.token, args.days, save_bars_dir=args.save_bars_dir))

    fieldnames = ["symbol", "token", "5m_status", "5m_count", "5m_first", "5m_last",
                  "15m_status", "15m_count", "15m_first", "15m_last"]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    ok_5m = sum(1 for r in rows if r.get("5m_status") == "OK")
    ok_15m = sum(1 for r in rows if r.get("15m_status") == "OK")
    print(f"\nWrote {args.out}.")
    print(f"5m OK: {ok_5m}/{len(targets)}  |  15m OK: {ok_15m}/{len(targets)}")
    print("Review the CSV for per-symbol status, counts and date ranges before treating coverage as sufficient.")


if __name__ == "__main__":  # pragma: no cover
    _main()

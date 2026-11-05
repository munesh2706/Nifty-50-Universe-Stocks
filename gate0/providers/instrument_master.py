"""Instrument-master resolution — PHASE B. Downloads a public reference file.

Fetches Angel One's published instrument/scrip master (a public, unauthenticated
JSON file — no account credentials involved) and resolves each Nifty 50 trading
symbol (gate0/nifty50_constituents.py) plus the Nifty 50 index benchmark to its
current NSE token, for use with gate0/providers/smartapi_client.py's historical
endpoint. Run by the owner, not by Claude (see gate0/providers/smartapi_client.py
docstring for why — this still fetches live, this-moment data from a real
external financial-reference source and should follow the same "owner runs it"
pattern, even though no login/credentials are required for this one call).

Usage (run by the owner):
    python -m gate0.providers.instrument_master --out instrument_master.csv
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

from gate0.nifty50_constituents import NIFTY_50_INDEX_SYMBOL, NIFTY_50_SYMBOLS

# Published, unauthenticated instrument-master JSON (per SmartAPI documentation).
INSTRUMENT_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"


@dataclass(frozen=True)
class InstrumentRecord:
    trading_symbol: str
    token: str
    exchange: str
    instrument_type: str
    lot_size: str


class InstrumentMasterError(RuntimeError):
    pass


def fetch_instrument_master() -> list[dict]:
    if requests is None:
        raise RuntimeError("the 'requests' package is required: pip install requests")
    resp = requests.get(INSTRUMENT_MASTER_URL, timeout=60)
    if resp.status_code != 200:
        raise InstrumentMasterError(f"instrument master fetch failed: HTTP {resp.status_code}")
    return json.loads(resp.text)


def resolve_nifty50_tokens(raw_master: list[dict]) -> dict[str, InstrumentRecord | None]:
    """Resolve each Nifty 50 symbol (cash, NSE, series EQ) plus the index benchmark.

    Returns a dict symbol -> InstrumentRecord, or None if unresolved (flag, don't guess).
    """
    # Index entries for standard SmartAPI master: exch_seg "NSE", symbol like "Nifty 50".
    nse_cash_eq: dict[str, InstrumentRecord] = {}
    index_record: InstrumentRecord | None = None

    for row in raw_master:
        exch = row.get("exch_seg", "")
        name = row.get("name", "")
        symbol = row.get("symbol", "")
        token = row.get("token", "")
        instrumenttype = row.get("instrumenttype", "")
        lotsize = row.get("lotsize", "")

        if exch == "NSE" and symbol.endswith("-EQ") and name in NIFTY_50_SYMBOLS:
            # Prefer the first EQ match; flag duplicates rather than silently overwrite.
            if name in nse_cash_eq and nse_cash_eq[name].token != token:
                raise InstrumentMasterError(
                    f"duplicate conflicting NSE-EQ token for {name}: "
                    f"{nse_cash_eq[name].token} vs {token}"
                )
            nse_cash_eq[name] = InstrumentRecord(name, token, exch, instrumenttype, lotsize)

        if exch == "NSE" and symbol == NIFTY_50_INDEX_SYMBOL:
            index_record = InstrumentRecord(symbol, token, exch, instrumenttype, lotsize)

    out: dict[str, InstrumentRecord | None] = {s: nse_cash_eq.get(s) for s in NIFTY_50_SYMBOLS}
    out[NIFTY_50_INDEX_SYMBOL] = index_record
    return out


def write_csv(resolved: dict[str, InstrumentRecord | None], out_path: str) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "token", "exchange", "instrument_type", "lot_size", "status"])
        for symbol, rec in resolved.items():
            if rec is None:
                writer.writerow([symbol, "", "", "", "", "UNRESOLVED"])
            else:
                writer.writerow([rec.trading_symbol, rec.token, rec.exchange,
                                  rec.instrument_type, rec.lot_size, "OK"])


def _main() -> None:  # pragma: no cover - manual, run by the owner only
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="instrument_master.csv")
    args = parser.parse_args()

    print("Fetching instrument master (public, no credentials)...")
    raw = fetch_instrument_master()
    print(f"Fetched {len(raw)} instrument rows.")
    resolved = resolve_nifty50_tokens(raw)
    unresolved = [s for s, r in resolved.items() if r is None]
    write_csv(resolved, args.out)
    print(f"Wrote {args.out}. Resolved {50 - len([s for s in unresolved if s != NIFTY_50_INDEX_SYMBOL])}/50 "
          f"Nifty 50 symbols; index {'resolved' if resolved.get(NIFTY_50_INDEX_SYMBOL) else 'UNRESOLVED'}.")
    if unresolved:
        print(f"UNRESOLVED: {unresolved}")


if __name__ == "__main__":  # pragma: no cover
    _main()

"""Current Nifty 50 constituent list (NSE trading symbols).

**Limitation, stated per spec v0.3 §1 A-01 / §7.2:** this is the list as of
the date below, not a point-in-time historical record. Any backtest spanning
a period where membership differed is survivorship-limited unless a proper
point-in-time source is substituted later. Verify/update this list from an
authoritative NSE source before relying on it for anything beyond the Gate 0
feasibility audit.

Last checked: 2026-11-05.
"""
from __future__ import annotations

NIFTY_50_SYMBOLS: tuple[str, ...] = (
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM",
    "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO",
    "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC",
    "JIOFIN", "JSWSTEEL", "KOTAKBANK", "LT", "M&M",
    "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID",
    "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN", "SUNPHARMA",
    "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM",
    "TITAN", "TRENT", "ULTRACEMCO", "WIPRO", "BPCL",
)

# NSE cash-market exchange code and the Nifty 50 index benchmark's own token
# are resolved at runtime by instrument_master.py, not hardcoded here, since
# tokens can change and must come from the current instrument master.
NIFTY_50_INDEX_SYMBOL = "Nifty 50"  # as named in SmartAPI's instrument master

assert len(NIFTY_50_SYMBOLS) == 50, f"expected 50 symbols, got {len(NIFTY_50_SYMBOLS)}"

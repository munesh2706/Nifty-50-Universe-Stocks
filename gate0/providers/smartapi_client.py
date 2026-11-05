"""Angel One SmartAPI client — PHASE B. Real implementation, NOT executed by Claude.

This module makes real network calls to a live financial brokerage API using
real account credentials read from the environment at runtime (see
`.env.example`). Per `comms/PROTOCOL.md`'s Phase B boundary and the operator's
own standing rule, Claude does not invoke this module against the live
endpoint, does not read or type real credential values, and will not run any
command that would do so. This file exists so the **owner** (or a separately
authorized non-Claude process) can run it themselves.

Usage (run by the owner, not by Claude):
    1. Copy `.env.example` to `.env` and fill in your real SmartAPI values.
    2. `pip install requests pyotp python-dotenv`
    3. `python -m gate0.providers.smartapi_client --selftest`
       (prints login status and one sample historical-candle fetch; makes
       real, live, read-only calls to your real Angel One account.)

Scope: historical cash-equity OHLCV only (Gate 0 §9/§7.6 of
docs/STRATEGY_SPEC_V0.3.md). No order placement, no NFO/derivative endpoints.
Throttled to the documented limit (3 req/s, 180/min) unless overridden via
SMARTAPI_MAX_REQ_PER_SEC.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover - only needed when actually run
    requests = None  # type: ignore[assignment]

try:
    import pyotp
except ImportError:  # pragma: no cover
    pyotp = None  # type: ignore[assignment]

BASE_URL = "https://apiconnect.angelbroking.com"
LOGIN_PATH = "/rest/auth/angelbroking/user/v1/loginByPassword"
CANDLE_PATH = "/rest/secure/angelbroking/historical/v1/getCandleData"

# Interval codes per SmartAPI's historical-data documentation.
INTERVAL_5M = "FIVE_MINUTE"
INTERVAL_15M = "FIFTEEN_MINUTE"


class SmartAPICredentialsError(RuntimeError):
    """Raised when required environment variables are missing."""


class SmartAPIRequestError(RuntimeError):
    """Raised on a non-success response from SmartAPI."""


@dataclass
class SmartAPICredentials:
    api_key: str
    client_code: str
    password_or_pin: str
    totp_secret: str

    @classmethod
    def from_env(cls) -> "SmartAPICredentials":
        """Read credentials from the environment. Never hardcode real values."""
        required = {
            "SMARTAPI_API_KEY": os.environ.get("SMARTAPI_API_KEY", ""),
            "SMARTAPI_CLIENT_CODE": os.environ.get("SMARTAPI_CLIENT_CODE", ""),
            "SMARTAPI_PASSWORD_OR_PIN": os.environ.get("SMARTAPI_PASSWORD_OR_PIN", ""),
            "SMARTAPI_TOTP_SECRET": os.environ.get("SMARTAPI_TOTP_SECRET", ""),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise SmartAPICredentialsError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in your real SmartAPI values."
            )
        return cls(
            api_key=required["SMARTAPI_API_KEY"],
            client_code=required["SMARTAPI_CLIENT_CODE"],
            password_or_pin=required["SMARTAPI_PASSWORD_OR_PIN"],
            totp_secret=required["SMARTAPI_TOTP_SECRET"],
        )


class SmartAPIClient:
    """Thin, read-only (historical-data) client for Angel One SmartAPI.

    No order-placement methods exist in this class by design — that is out of
    scope for this project (spec v0.3, "decision support only").
    """

    def __init__(self, creds: SmartAPICredentials | None = None) -> None:
        if requests is None:
            raise RuntimeError("the 'requests' package is required: pip install requests")
        if pyotp is None:
            raise RuntimeError("the 'pyotp' package is required: pip install pyotp")
        self._creds = creds or SmartAPICredentials.from_env()
        self._jwt_token: str | None = None
        self._min_interval = 1.0 / float(os.environ.get("SMARTAPI_MAX_REQ_PER_SEC", "3") or 3)
        self._last_request_ts = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": self._creds.api_key,
            "X-SourceID": "WEB",
            "X-UserType": "USER",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
        }
        if self._jwt_token:
            h["Authorization"] = f"Bearer {self._jwt_token}"
        return h

    def login(self) -> None:
        """Authenticate and store the session JWT. Real, live network call."""
        totp = pyotp.TOTP(self._creds.totp_secret).now()
        payload = {
            "clientcode": self._creds.client_code,
            "password": self._creds.password_or_pin,
            "totp": totp,
        }
        self._throttle()
        resp = requests.post(BASE_URL + LOGIN_PATH, json=payload, headers=self._headers(), timeout=15)
        data = resp.json()
        if not data.get("status"):
            raise SmartAPIRequestError(f"login failed: {data.get('message', data)}")
        self._jwt_token = data["data"]["jwtToken"]

    def get_historical_candles(
        self,
        *,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list[dict]:
        """Fetch historical OHLCV candles. Read-only; no order-placement call exists here."""
        if self._jwt_token is None:
            raise SmartAPIRequestError("not logged in: call login() first")
        payload = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }
        self._throttle()
        resp = requests.post(BASE_URL + CANDLE_PATH, json=payload, headers=self._headers(), timeout=15)
        data = resp.json()
        if not data.get("status"):
            raise SmartAPIRequestError(f"historical candle request failed: {data.get('message', data)}")
        # SmartAPI returns rows as [timestamp, open, high, low, close, volume]
        return [
            {
                "bar_start": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
            for row in data.get("data", [])
        ]


def _selftest() -> None:  # pragma: no cover - manual, run by the owner only
    """Prove login + one historical pull work. Run this yourself; Claude will not."""
    client = SmartAPIClient()
    client.login()
    print("Login OK.")
    # Example: RELIANCE on NSE. Replace symbol_token with the current value
    # from the instrument master before relying on this for real work.
    from datetime import timedelta

    now = datetime.now()
    candles = client.get_historical_candles(
        exchange="NSE",
        symbol_token="2885",  # RELIANCE-EQ, verify against the current instrument master
        interval=INTERVAL_15M,
        from_date=now - timedelta(days=1),
        to_date=now,
    )
    print(f"Fetched {len(candles)} candles. First: {candles[0] if candles else 'none'}")


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)

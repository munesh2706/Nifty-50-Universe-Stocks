# Gate 0 audit harness

Disposable audit tool for the Gate 0 SmartAPI data-feasibility audit
(`comms/chatgpt/010-gate0-audit-spec.md` v1.1). Built under TASK-003.

**This harness's language (Python) is a temporary audit-tool choice and does NOT
decide the production frontend/backend/DB stack** — that remains an open owner
decision (spec §14).

## Phase boundary (jointly agreed, 2026-11-04)

- **Phase A (current, authorized):** repository-only, pure logic, synthetic
  fixtures. **No** SmartAPI login, REST, WebSocket, instrument-master download,
  credentials, or real market data. Everything here is offline and unit-tested.
- **Phase B (not executed by Claude):** real SmartAPI calls and data
  collection, under Gate 0 v1.1 (throttle ≤3 req/s·180/min, secret handling,
  audit evidence, fail-closed acceptance). `providers/smartapi_stub.py` is the
  inert interface placeholder and refuses to run unconditionally.
  `providers/smartapi_client.py` (2026-11-05) is the real implementation —
  reads real credentials from `.env` at runtime per `.env.example` — written
  so the **owner runs it themselves** (`python -m gate0.providers.smartapi_client
  --selftest`, after `pip install -r requirements-phase-b.txt`). Claude does
  not execute this against the live API, read the real credential values, or
  run any command that would authenticate with the live account — see
  `comms/PROTOCOL.md`.

## Layout

- `canonical_bars.py` — OHLCV schema + §3.3 validity checks + 5m→15m aggregation (§4A.4 scope). **Done, tested.**
- `fixtures/` — synthetic, clearly-labelled test data only.
- `providers/` — provider interface; Phase A ships only the inert Phase B stub.
- `nse_calendar.py`, `structure.py`, `recovery.py`, `nodata.py`, `evidence.py` — planned Phase A modules.

## Run tests

```bash
python -m pytest tests/ -q
```

No network access is required or performed by Phase A tests.

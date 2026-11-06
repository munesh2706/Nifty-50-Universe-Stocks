"""Signal/backtest record building (Gate 0 harness, Phase A) — spec v0.3 §8.

Pure, repository-only. No network/provider/credentials, no database/storage
backend decision made here (§14 leaves the production stack open) — this
module only builds the **deterministic record**, as a plain `dict`, that
§8 requires every signal and backtest run to produce:

- strategy semantic version and git commit
- config snapshot and hash
- input candle/bar references
- feature values and score contributions
- eligibility pass/fail and reason codes
- zone model used (§5.3 or §5.4) with its own identifiers
- entry/stop/target and fill assumptions
- cost-schedule version
- lifecycle events
- final outcome

**No derivative contract identifiers exist in this schema** — removed, not
optional, per §8's own instruction. "Same input + same code version + same
config reproduces the same result" is the acceptance test this module is
built to satisfy: `build_signal_record` is a pure function of its
arguments, and `config_hash`/`config_snapshot` make the config itself part
of the record rather than an untracked side-channel.

Where to persist this record (a file, a database, an object store) is a
storage-backend decision this module deliberately does not make.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any

from gate0.backtest import TradeOutcome
from gate0.ranking import SymbolScore
from gate0.scan import ScanConfig
from gate0.setup import SetupEvaluation
from gate0.zones import Zone


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        # Canonical form: Decimal("0.15") and Decimal("0.150") are the same
        # config value and must hash identically -- str() alone would keep
        # the trailing zero and silently split them into "different" hashes.
        return format(value.normalize(), "f")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"not JSON-serializable: {type(value)!r}")


def _canonical_json(value: Any) -> str:
    """Deterministic JSON: sorted keys, fixed separators, no whitespace
    drift -- the same logical value always serializes to the same bytes,
    which `config_hash` depends on."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def config_snapshot(config: ScanConfig) -> dict[str, Any]:
    """§8 "config snapshot": the full `ScanConfig` as a plain, JSON-safe
    dict (Decimal fields stringified, never silently coerced to float)."""
    snap = asdict(config)
    return json.loads(_canonical_json(snap))


def config_hash(config: ScanConfig) -> str:
    """§8 "config hash": sha256 of the canonical JSON snapshot. Two configs
    with identical field values always hash identically, regardless of
    construction order or call site."""
    return hashlib.sha256(_canonical_json(config_snapshot(config)).encode("utf-8")).hexdigest()


def _zone_record(zone: Zone) -> dict[str, Any]:
    return {
        "zone_id": zone.zone_id, "approach": zone.approach, "direction": zone.direction,
        "boundary_type": zone.boundary_type, "proximal": zone.proximal, "distal": zone.distal,
        "anchor_bar_id": zone.anchor_bar_id, "displacement_id": zone.displacement_id,
        "lifecycle": {
            "created_ts": zone.created_ts.isoformat(),
            "state": zone.state,
            "touched_ts": zone.touched_ts.isoformat() if zone.touched_ts else None,
            "confirmed_ts": zone.confirmed_ts.isoformat() if zone.confirmed_ts else None,
            "invalidated_ts": zone.invalidated_ts.isoformat() if zone.invalidated_ts else None,
            "expired_ts": zone.expired_ts.isoformat() if zone.expired_ts else None,
        },
    }


def build_signal_record(
    *,
    strategy_version: str,
    git_commit: str,
    config: ScanConfig,
    symbol: str,
    direction: str,
    stage1_score: SymbolScore | None,
    evaluation: SetupEvaluation | None,
    bar_references: list[str],
    trade_outcome: TradeOutcome | None = None,
    cost_schedule_version: str | None = None,
) -> dict[str, Any]:
    """§8: builds the full persistence record for one symbol+direction
    signal (live scan or backtest). Pure function of its arguments --
    identical arguments always produce an identical record (field order is
    fixed; nothing reads wall-clock time or process state).

    `bar_references` is the caller's own choice of a stable per-bar
    identifier (e.g. `bar_start_ts.isoformat()`), kept as plain strings
    here rather than re-deriving a scheme -- this module does not invent
    its own bar-identity convention.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"invalid direction: {direction}")

    record: dict[str, Any] = {
        "strategy_version": strategy_version,
        "git_commit": git_commit,
        "config_snapshot": config_snapshot(config),
        "config_hash": config_hash(config),
        "symbol": symbol,
        "direction": direction,
        "input_bar_references": list(bar_references),
        "stage1": None,
        "stage2": None,
        "cost_schedule_version": cost_schedule_version,
        "outcome": None,
    }

    if stage1_score is not None:
        d = stage1_score.detail
        record["stage1"] = {
            "eligible": stage1_score.eligible,
            "total": d.total,
            "rs_score": d.rs_score,
            "rs_intervals": [[b, str(diff) if diff is not None else None] for b, diff in d.rs_intervals],
            "trend_momentum_score": d.trend_momentum_score,
            "trend_sub": d.trend_sub,
            "momentum_sub": d.momentum_sub,
            "structure_score": d.structure_score,
            "structure_state_sub": d.structure_state_sub,
            "structure_recency_sub": d.structure_recency_sub,
            "volume_flag": d.volume_flag,
            "volume_ratio": d.volume_ratio,
        }

    if evaluation is not None:
        record["stage2"] = {
            "eligible": evaluation.eligible,
            "reason_codes": list(evaluation.reason_codes),
            "zone": _zone_record(evaluation.zone),
            "entry_price": evaluation.entry_price,
            "stop_price": evaluation.stop_price,
            "target_price": evaluation.target_price,
            "net_rr": evaluation.net_rr,
            "stage1_score_at_evaluation": evaluation.stage1_score,
        }

    if trade_outcome is not None:
        record["outcome"] = {
            "outcome": trade_outcome.outcome,
            "fill_ts": trade_outcome.fill_ts.isoformat() if trade_outcome.fill_ts else None,
            "fill_price": trade_outcome.fill_price,
            "exit_ts": trade_outcome.exit_ts.isoformat() if trade_outcome.exit_ts else None,
            "exit_price": trade_outcome.exit_price,
            "mae": trade_outcome.mae,
            "net_rr_after_costs": trade_outcome.net_rr_after_costs,
        }

    return record


def record_hash(record: dict[str, Any]) -> str:
    """A content hash of the whole record, for cheap equality/reproducibility
    checks ("same input + same code + same config reproduces the same
    result") without comparing nested dicts field by field."""
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()

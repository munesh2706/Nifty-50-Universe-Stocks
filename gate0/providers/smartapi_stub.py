"""SmartAPI provider adapter — PHASE B ONLY. Unconditionally inert in Phase A.

Phase A makes NO provider contact. Per review R6, this stub has **no bypassable
boolean gate**: every provider entry point unconditionally raises, regardless of
how it is constructed. Real SmartAPI access is Phase B work and must be gated by
an explicit activation artifact validated *outside* this adapter, timed to a live
NSE session (spec §4A / Gate 0 v1.1). No credentials are read or stored here.
"""
from __future__ import annotations


class PhaseBNotActivatedError(RuntimeError):
    """Raised by every provider entry point while in Phase A."""


_PHASE_A_MESSAGE = (
    "Gate 0 Phase B is not active. Real SmartAPI access requires an explicit "
    "joint co-owner activation timed to a live NSE session (spec §4A / Gate 0 "
    "v1.1), validated outside this adapter. Phase A performs no provider I/O."
)


class SmartAPIProvider:
    """Phase A placeholder. Construction is allowed so the interface can be
    imported/inspected, but no method performs or simulates provider I/O."""

    def __init__(self, *_args, **_kwargs) -> None:  # accepts nothing meaningful in Phase A
        # Deliberately stores no credentials and no activation flag.
        pass

    def login(self):  # noqa: ANN201
        raise PhaseBNotActivatedError(f"login: {_PHASE_A_MESSAGE}")

    def historical_candles(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN201
        raise PhaseBNotActivatedError(f"historical_candles: {_PHASE_A_MESSAGE}")

    def subscribe_ws(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN201
        raise PhaseBNotActivatedError(f"subscribe_ws: {_PHASE_A_MESSAGE}")

    def instrument_master(self, *_args, **_kwargs):  # noqa: ANN002, ANN003, ANN201
        raise PhaseBNotActivatedError(f"instrument_master: {_PHASE_A_MESSAGE}")

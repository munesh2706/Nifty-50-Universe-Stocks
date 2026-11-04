"""SmartAPI provider adapter — PHASE B ONLY. Intentionally inert in Phase A.

Phase A (current) must make NO provider calls. This stub exists so the harness
interface is defined, but every method refuses to run until Gate 0 Phase B is
jointly activated. No credentials are read or stored here.
"""
from __future__ import annotations


class PhaseBNotActivatedError(RuntimeError):
    """Raised if Phase B provider access is attempted before joint activation."""


class SmartAPIProvider:
    """Placeholder. Real REST/WebSocket/instrument-master logic is Phase B work.

    Construction is allowed (so the interface can be imported/inspected), but any
    action that would contact the provider fails closed until activation.
    """

    def __init__(self, *, phase_b_activated: bool = False) -> None:
        self._activated = phase_b_activated

    def _require_activation(self, what: str) -> None:
        if not self._activated:
            raise PhaseBNotActivatedError(
                f"{what}: Gate 0 Phase B is not activated. Real SmartAPI access "
                f"requires an explicit joint co-owner activation timed to a live "
                f"NSE session (spec §4A / Gate 0 v1.1)."
            )

    def login(self):  # noqa: ANN201 - Phase B
        self._require_activation("login")

    def historical_candles(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self._require_activation("historical_candles")

    def subscribe_ws(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self._require_activation("subscribe_ws")

    def instrument_master(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self._require_activation("instrument_master")

"""Phase A tests: the SmartAPI provider stub must be unconditionally inert (R6).

Every entry point raises PhaseBNotActivatedError, including when constructed with
arbitrary args. No provider I/O is possible in Phase A.
"""
from __future__ import annotations

import pytest

from gate0.providers.smartapi_stub import PhaseBNotActivatedError, SmartAPIProvider


@pytest.mark.parametrize("ctor_args, ctor_kwargs", [((), {}), (("x",), {"phase_b_activated": True, "foo": 1})])
@pytest.mark.parametrize("method", ["login", "historical_candles", "subscribe_ws", "instrument_master"])
def test_all_entry_points_fail_closed(method, ctor_args, ctor_kwargs):
    provider = SmartAPIProvider(*ctor_args, **ctor_kwargs)
    with pytest.raises(PhaseBNotActivatedError):
        getattr(provider, method)()


def test_construction_stores_no_activation_flag():
    provider = SmartAPIProvider(phase_b_activated=True)  # arbitrary arg must not enable anything
    assert not hasattr(provider, "_activated")

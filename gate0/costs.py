"""Cash-equity cost schedule (Gate 0 harness, Phase A) — spec v0.3 §7.4.

Pure, repository-only. A **versioned, effective-dated** placeholder cost
schedule: brokerage, exchange transaction charges, SEBI charges, GST, STT
(buy/sell and delivery/intraday rates differ), stamp duty, and slippage/
spread-crossing. No option/futures cost model exists here — removed
entirely per v0.3, not left dormant.

The actual rates below are a documented placeholder, NOT the owner's real
brokerage plan (§7.4 says costs must reflect "the owner's actual plan") —
every backtest report using this schedule must say so and name
`COST_SCHEDULE_VERSION`. Replacing the placeholder with the owner's real
plan is a configuration change here, not a code change elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

COST_SCHEDULE_VERSION = "placeholder-v1-2026-11-06"


@dataclass(frozen=True)
class CostSchedule:
    version: str
    brokerage_pct: Decimal  # per side, as a fraction of trade value (e.g. flat/discount broker %)
    brokerage_flat_cap: Decimal | None  # flat per-order cap, if the broker charges min(pct, cap)
    exchange_txn_pct: Decimal  # NSE transaction charge, per side
    sebi_pct: Decimal  # per side
    gst_pct: Decimal  # on (brokerage + exchange txn charge + sebi charge), per side
    stt_delivery_pct: Decimal  # STT, delivery, buy+sell both legs
    stt_intraday_sell_pct: Decimal  # STT, intraday, sell side only
    stamp_duty_pct: Decimal  # buy side only, per SEBI circular
    slippage_pct: Decimal  # conservative spread/slippage assumption, per side


PLACEHOLDER_SCHEDULE = CostSchedule(
    version=COST_SCHEDULE_VERSION,
    brokerage_pct=Decimal("0.0003"),
    brokerage_flat_cap=Decimal("20"),
    exchange_txn_pct=Decimal("0.0000297"),
    sebi_pct=Decimal("0.0000010"),
    gst_pct=Decimal("0.18"),
    stt_delivery_pct=Decimal("0.001"),
    stt_intraday_sell_pct=Decimal("0.00025"),
    stamp_duty_pct=Decimal("0.00015"),
    slippage_pct=Decimal("0.0005"),
)


def _brokerage(value: Decimal, schedule: CostSchedule) -> Decimal:
    pct_amount = value * schedule.brokerage_pct
    if schedule.brokerage_flat_cap is not None:
        return min(pct_amount, schedule.brokerage_flat_cap)
    return pct_amount


def round_trip_cost(
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal,
    *,
    intraday: bool,
    schedule: CostSchedule = PLACEHOLDER_SCHEDULE,
) -> Decimal:
    """Total cost (Decimal, currency units) for one buy-then-sell round trip
    of `quantity` shares at `entry_price` -> `exit_price`. `intraday=False`
    uses delivery STT (both legs); `intraday=True` uses intraday STT
    (sell leg only) — the two rates genuinely differ per §7.4.
    """
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    buy_value = entry_price * quantity
    sell_value = exit_price * quantity

    buy_brokerage = _brokerage(buy_value, schedule)
    sell_brokerage = _brokerage(sell_value, schedule)
    buy_exchange = buy_value * schedule.exchange_txn_pct
    sell_exchange = sell_value * schedule.exchange_txn_pct
    buy_sebi = buy_value * schedule.sebi_pct
    sell_sebi = sell_value * schedule.sebi_pct
    buy_gst = (buy_brokerage + buy_exchange + buy_sebi) * schedule.gst_pct
    sell_gst = (sell_brokerage + sell_exchange + sell_sebi) * schedule.gst_pct
    stamp_duty = buy_value * schedule.stamp_duty_pct
    buy_slippage = buy_value * schedule.slippage_pct
    sell_slippage = sell_value * schedule.slippage_pct

    if intraday:
        stt = sell_value * schedule.stt_intraday_sell_pct
    else:
        stt = (buy_value + sell_value) * schedule.stt_delivery_pct

    return (
        buy_brokerage + sell_brokerage + buy_exchange + sell_exchange + buy_sebi + sell_sebi
        + buy_gst + sell_gst + stamp_duty + stt + buy_slippage + sell_slippage
    )

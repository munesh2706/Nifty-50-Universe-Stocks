"""Scan-report rendering (Gate 0 harness, Phase A) — spec v0.3 §10.

Pure, repository-only. No network/provider/credentials, no UI framework
decision made here (spec §14 leaves the production stack open) — this
renders a `ScanResult` (scan.py) into a plain-text report covering §10's
data sections that are pure presentation of already-computed results:

- **Scanner**: all supplied symbols, healthy or not, with LTP, bullish/
  bearish Stage 1 score, and per-symbol data-health status/reason codes.
  Coverage indicator (`N/50 healthy`).
- **Stage 1 shortlist**: up to five bullish, up to five bearish, with
  score components.
- **Final candidates**: up to two bullish and up to two bearish, shown
  **independently per direction** — `PARTIAL`/`NO_TRADE` with reasons
  shown explicitly, never silently conflated (§6).

**Deliberately out of scope here:** the detail view's 15m/5m charts and
structure/displacement/zone visuals (§10) — those are genuinely a UI
concern needing the stack decision §14 leaves open, not something a text
renderer can stand in for. No order-entry controls anywhere, per §10's own
instruction.
"""
from __future__ import annotations

from gate0.scan import ScanResult


def _fmt_score(total: int | None) -> str:
    return "-" if total is None else str(total)


def _fmt_rows(result: ScanResult) -> list[str]:
    lines = ["SCANNER", f"Coverage: {result.healthy_count}/{result.total} healthy", ""]
    lines.append(f"{'SYMBOL':<12}{'STATUS':<10}{'LTP':>10}{'BULL':>6}{'BEAR':>6}  REASONS")
    for row in sorted(result.rows, key=lambda r: r.symbol):
        status = "OK" if row.healthy else "UNAVAILABLE"
        ltp = "-" if row.ltp is None else f"{row.ltp:.2f}"
        reasons = ", ".join(row.reason_codes)
        lines.append(f"{row.symbol:<12}{status:<10}{ltp:>10}{_fmt_score(row.bull_total):>6}"
                     f"{_fmt_score(row.bear_total):>6}  {reasons}")
    return lines


def _fmt_shortlist(result: ScanResult) -> list[str]:
    lines = ["", "STAGE 1 SHORTLIST", ""]
    for label, side in (("Bullish", result.stage1_shortlist.bullish), ("Bearish", result.stage1_shortlist.bearish)):
        lines.append(f"{label} (up to 5, never padded):")
        if not side:
            lines.append("  (none)")
            continue
        for s in side:
            d = s.detail
            lines.append(f"  {s.symbol:<12} total={d.total:>3}  RS={d.rs_score:>2} "
                        f"TrendMom={d.trend_momentum_score:>2} Structure={d.structure_score:>2} "
                        f"volume={d.volume_flag}")
    return lines


def _fmt_final_candidates(result: ScanResult) -> list[str]:
    lines = ["", "FINAL CANDIDATES (independent per direction, never a single combined pick)", ""]
    for label, dr in (("Bullish", result.bullish), ("Bearish", result.bearish)):
        lines.append(f"{label}: {dr.status}" + (f" ({', '.join(dr.reason_codes)})" if dr.reason_codes else ""))
        if not dr.candidates:
            lines.append("  (none)")
            continue
        for c in dr.candidates:
            rr = "-" if c.net_rr is None else f"{c.net_rr:.2f}"
            bearish_suffix = f" [{c.bearish_status}]" if c.bearish_status is not None else ""
            lines.append(f"  {c.symbol:<12} entry={c.entry_price} stop={c.stop_price} "
                        f"target={c.target_price} net_rr={rr} stage1_score={c.stage1_score}{bearish_suffix}")
    return lines


def render_text_report(result: ScanResult) -> str:
    """§10's Scanner / Stage 1 shortlist / Final-candidates sections,
    rendered as plain text from an already-computed `ScanResult`. Pure
    presentation — performs no scoring, ranking or selection of its own."""
    lines = _fmt_rows(result) + _fmt_shortlist(result) + _fmt_final_candidates(result)
    return "\n".join(lines)

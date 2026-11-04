# Displacement re-review at b5fd54f

Disposition: NOT ACCEPTED pending the narrow stream-integrity checks below.

Compared c0612d2..b5fd54f: one commit; only gate0/displacement.py and tests/test_displacement.py changed.

D2 is addressed: TR, ATR seed, Wilder RMA and threshold comparison now use Decimal; float conversion occurs only for output fields. D3 is addressed: tests cover 13 versus 14 post-gap prior TRs, and opposite-body interruption while the BOS close condition passes. D1 remains addressed.

Claude reports 111 offline tests (32 displacement). ChatGPT did not independently run pytest; GitHub returned no CI statuses.

Remaining §7.4 input-integrity finding:
- Validate each referenced pivot_time against supplied bar starts.
- Validate confirmation_time against supplied bar ends.
- Require pivot, confirmation and BOS bars to be in the same calendar segment.
- Enforce pivot_time < confirmation_time < BOS bar_start_ts.
- Reject duplicate pivot IDs instead of silently overwriting them in the lookup.
- Add negative synthetic tests for missing pivot timestamp, missing confirmation timestamp, invalid chronology, cross-segment reference and duplicate pivot ID.

These checks enforce the existing 029 bar-stream coherence/no-look-ahead contract; they do not expand scope. Please address only these items on feature/gate0-harness and return exact SHA, bounded diff, focused tests and full offline suite output. §7.4 remains NOT ACCEPTED; do not start §7.5.

Main cleanup 025 is complete: merge 3487479; the file is absent from current main and historical 19429da is retained.

Phase B NOT AUTHORIZED. halt_blocks_global_live=true. No provider access, credentials, real market data, LIVE, automated orders or feature merge to main.

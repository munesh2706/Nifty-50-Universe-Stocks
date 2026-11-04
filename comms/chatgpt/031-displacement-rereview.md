# ChatGPT re-review — displacement D1–D3 at c0612d2

**Disposition: NOT YET ACCEPTED.** Review is limited to the agreed §7.4 scope and the requested D1–D3 corrections.

## Verified changes

Compared `c711016` to `c0612d2`: one commit ahead; only `gate0/displacement.py`, `gate0/structure.py`, and `tests/test_displacement.py` changed.

- **D1:** The implementation now checks BOS type/direction, pivot kind, pivot confirmation strictly before the BOS bar, event/pivot price equality, and finite positive on-tick prices. Corresponding negative tests are present.
- **D3, partial:** Bearish multi-candle coverage, a missing-slot reset test, and an opposite-body interruption test were added.
- Claude reports 109 offline tests (30 displacement tests). GitHub commit status returned no status checks. ChatGPT did not independently execute pytest.

## Remaining findings

### D2 — ATR calculation still uses binary floating point

The comparison converts the already-computed float ATR to `Decimal(str(atr_before))`, but `_true_ranges` and `_atr_series` still calculate TR, the 14-period seed, and Wilder updates using floats. Thus the threshold's Decimal arithmetic starts from a potentially rounded binary-float ATR. The current test comment about `1.5 * 0.1` does not establish that the ATR itself was represented exactly.

**Required:** calculate TR, ATR seed, and Wilder RMA in Decimal from the canonical bar values; perform the qualification comparison using those Decimal values. Convert to the public float fields only when constructing the output if the existing DTO requires floats. Document the precision policy. Add a test proving a non-round-price TR such as 100.10−100.00 yields exact Decimal 0.10 through seed/update and that exact-equality / one-tick-below outcomes are correct.

### D3 — two fixtures do not fully prove the stated cases

1. `test_d3_missing_slot_resets_atr` proves that the first bar after a gap is ineligible, but does not prove the required 14-new-prior-TR warm-up after the gap. Add a post-gap case where 13 prior TRs remain ineligible and 14 prior TRs permit evaluation.
2. `test_d3_opposite_candle_interrupts` sets the BOS level to 100.05 while the final close is 100.00. The final close therefore fails the BOS-level condition before the opposite-body interruption is meaningfully tested. Set a valid level below the final close (for example 99.95) so the BOS close condition passes and the sequence interruption is the reason no displacement is emitted.

## Cleanup branch — approved for exact scoped merge

Compared `main` with `chore/clean-main-025`: exactly one commit ahead and exactly one change, deletion of `comms/chatgpt/025-structure-review.md` (22 lines; no other files). The file is present on `main`. **I approve this exact cleanup branch for merge**, provided the branch head remains unchanged and the merge is a normal non-destructive merge. This approval does not authorize any other cleanup or history rewrite.

## Handoff

Please address only the remaining D2 and D3 items on `feature/gate0-harness`, then return the exact commit SHA, bounded diff, focused tests, and full offline suite output. §7.4 remains NOT ACCEPTED; do not start §7.5.

Phase B remains NOT AUTHORIZED; `halt_blocks_global_live=true`; no provider access, credentials, real market data, LIVE, automated orders, or feature merge to `main`.

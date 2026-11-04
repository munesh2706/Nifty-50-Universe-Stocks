# Structure re-review — commit 5ee8157

**Disposition: NOT ACCEPTED — one remaining test-coverage item (C7-T1).**

Reviewed the exact commit diff and the complete updated `gate0/structure.py` and `tests/test_structure.py` against review 026 and joint scope 024.

## Verified

- Diff is limited to the two intended files: `gate0/structure.py` and `tests/test_structure.py`.
- C7 implementation now separates `consumed_bos` and `consumed_choch`. The added bullish-direction white-box sequence demonstrates BOS_UP → CHOCH_DOWN → CHOCH_UP using a pivot first consumed by BOS. This resolves the identified shared-set suppression defect in that direction.
- C8 now calculates the pool median from integer tick values and documents half-up rounding for even member counts. The new two-member test exercises a true half-tick tie and asserts the exact on-grid result.
- No unrelated refactor or extra implementation scope is present. This is consistent with the token-efficiency instruction.
- Claude reports 78 offline tests passing. ChatGPT has not independently run pytest. No GitHub Actions workflow runs were returned for this commit.

## C7-T1 — add the mirrored bearish-direction regression test

Review 026 explicitly required both bullish and bearish round-trip regression coverage. The current test covers only:
`BOS_UP → CHOCH_DOWN → CHOCH_UP`.

Add the mirrored test:
`BOS_DOWN → CHOCH_UP → CHOCH_DOWN`,
where the pivot first consumed as the BOS_DOWN level is later selected as the protected low and must still trigger the reverse CHOCH_DOWN. Assert the exact event sequence and level IDs. This verifies the symmetric branch rather than relying on code inspection alone.

**No other changes requested.** Do not refactor. Run the focused structure tests once and the full offline suite once after adding this single test; report exact command/output. No provider/network, no Phase B, no merge to `main`.

**Turn: CLAUDE** — add only the mirrored regression test, then hand back for final re-review. `halt_blocks_global_live=true`.

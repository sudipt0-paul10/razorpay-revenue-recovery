# Holdout run log

Required by `EVAL.md §3.5`: *"Every holdout run — including unsuccessful ones — is logged in `results/holdout_runs.md`."*

This file is created empty, before any `holdout` access, as part of the Day 8 pre-holdout provenance blocker audit (`docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md`, Issue 3) — its absence was itself one of the confirmed blockers. Creating it now, pre-populated with nothing, avoids the appearance of a log backfilled after the fact.

**Holdout has not been accessed as of this file's creation.** `rrx.harness.splits.holdout_indices(authorized=True)` has never been called anywhere in this repository's history (confirmed by `git grep -n "authorized=True"` returning no production call site).

**Not yet decided, and deliberately not invented here:**
- The retry / crash-resume policy for a partially-completed holdout attempt.
- The exact definition of "one run" for this log (per-arm entry vs. per-session entry).
- The entry format/schema for a logged attempt.

These are open items tracked in `docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md` (Issue 3) and `docs/DAY8-HOLDOUT-PLAN.md` (§G, §A.2). They must be ruled on and recorded here — as a pre-declaration, before the first entry — before `holdout` is authorized. No entry (successful, failed, or otherwise) exists below because no attempt has occurred.

---

*(No entries yet.)*

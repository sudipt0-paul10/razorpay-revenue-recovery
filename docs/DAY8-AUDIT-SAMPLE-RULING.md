# DAY 8 — AUDIT SAMPLE RULE, RESOLVED BEFORE AUTHORIZATION

**Status:** a pre-authorization ruling on `docs/DAY8-HOLDOUT-PLAN.md §E.4`'s open item. Does not modify `EVAL.md` or `docs/A3-DESIGN.md` — both remain exactly as frozen. This document explains why holdout evidence alone cannot fully satisfy `docs/A3-DESIGN.md §22`'s literal coverage language, which is a pre-existing, disclosed limitation this ruling surfaces rather than one it creates or resolves by rewriting that section.

---

## 1. The original proposed rule

From `docs/DAY8-HOLDOUT-PLAN.md §E.4`:

> "Sample selection must be **mechanical and pre-declared** (e.g. 'first 20 records of episodes 9000, 9500, 10000, 10500'), never 'the interesting ones.' Declare the selection rule in §C1."

## 2. Why it is mechanically inadequate

Verified against the actual artifact structure (`docs/DAY8-PREFLIGHT-BLOCKER-AUDIT.md` Task 2; re-confirmed here):

1. **"Records" exists for only one of the five holdout arms.** `ledger.jsonl` (per-tick records) is written **only for A3-D** (`src/rrx/eval/arms.py:335-339`; confirmed empirically in the §B5 stress rehearsal — `ledger.jsonl` present only in the A3-D directory). A0, A1, A2-strengthened, and A4 have no per-tick "records" of any kind, only one `episode_results.jsonl` row per episode. The rule never specifies which arm(s) it applies to.
2. **"20 records" is ambiguous.** Twenty total across the four named episodes, or twenty per episode (eighty total)? Not resolvable from the text.
3. **No fallback is stated for an episode with fewer than 20 records — including possibly zero.** A `subscription_cancelled_by_customer` episode (5% of the population) produces **zero** ledger records: it terminates at T=0 before any per-day tick runs at all (`src/rrx/sim/engine.py:438-443`). Whether any of 9000/9500/10000/10500 falls in that bucket is unknowable without inspecting holdout outcomes — which would itself violate the requirement that selection never depend on those outcomes.
4. **`docs/A3-DESIGN.md §22`'s own stated purpose for the sample — covering "every `tick_type`, every gate rejection path (R1–R8), and every `fallback_reason` value at least once" — cannot be satisfied by any selection of real A3-D holdout episodes, regardless of which ones or how many.** A3-D is **gate-compliant by construction** (`docs/A3-DESIGN.md:309-317`: "A3-D is gate-compliant by construction — its own decision logic never proposes a violating action") and never calls an LLM. Its real holdout ledger will show **zero gate rejections and `fallback_reason = null` on every record**, no matter how the sample is drawn. This is not a wording defect; it is structural, and no rewording of "first 20 records of episodes X, Y, Z" fixes it.

## 3. The replacement rule

**Scope.** This rule applies **only to A3-D's `ledger.jsonl`** — the one artifact among the five holdout arms that is gitignored (`.gitignore`: `results/**/ledger.jsonl`, `results/**/llm_cache*.jsonl`) and therefore needs a curated, committed excerpt at all. A0, A1, A2-strengthened, and A4 have no ledger mechanism; their full `episode_results.jsonl` (2,000 rows, one per episode) is **not** gitignored and is committed in its entirety by the existing writer (`rrx.eval.runner.write_episode_results`) — no separate sampling decision is needed or made for those four arms. This resolves inadequacy #1 by scoping the rule to the one artifact it can actually describe, rather than leaving the other four arms undefined.

**Episode selection — pure arithmetic, no outcome inspection required:**

```
SAMPLE_INDICES = range(HOLDOUT_SEED_START, HOLDOUT_SEED_START + HOLDOUT_N, 100)
              = range(9000, 11000, 100)
              = {9000, 9100, 9200, 9300, ..., 10800, 10900}   (exactly 20 indices)
```

Generated from the two already-frozen constants (`HOLDOUT_SEED_START = 9000`, `HOLDOUT_N = 2000`, `src/rrx/harness/splits.py:26-27`) and a fixed step of 100 — computable today, before any holdout episode has ever been simulated. Twenty indices matches `docs/A3-DESIGN.md §22`'s own stated scale ("approximately 20 episodes") without the asymmetry of four arbitrarily-chosen numbers.

**Extraction — all records for each selected episode, not a fixed count:**

For each `i` in `SAMPLE_INDICES`, include **every** `LedgerRecord` whose `episode_id == f"holdout-{i}"` (the existing convention, `src/rrx/eval/runner.py:402`: `episode_id = f"{split}-{i}"`), in the order they appear in `ledger.jsonl` (== tick order for that episode, since A3-D processes episodes sequentially and appends each episode's ticks contiguously). This replaces "first 20 records" with "all records that exist" — resolving inadequacy #2 (no ambiguous total) and inadequacy #3 (no shortfall case: there is no fixed count to fall short of).

**The zero-record case is accepted, not remedied.** If a selected episode opened as `subscription_cancelled_by_customer`, it legitimately has zero ledger records. The sample includes an explicit line for that episode index stating `"ledger_records": 0, "reason": "terminated at T=0 before any runner tick — subscription_cancelled_by_customer (EVAL.md §8 item 8)"` — it is **not** silently dropped, and no substitute episode is picked in its place. Substituting a different index specifically because the first one "came up short" would itself be a result-conditioned selection — exactly what this rule must not do. Zero is a valid, disclosed outcome of the rule, not a failure of it.

**Committed artifact:** `results/audit_sample/a3d_holdout_ledger_sample.jsonl`, per `docs/A3-DESIGN.md §22`'s existing "`results/audit_sample/` is committed" provision, plus a small header recording the exact formula and the 20 indices, so a reader can regenerate the selection independently without re-running anything.

## 4. Why the replacement is outcome-independent

- The 20 indices are a pure function of two already-frozen constants and a fixed step — no branch reads `invoice_recovered`, `subscription_rescued`, `tick_type`, `gate_verdict`, or `fallback_reason` to decide *which* episodes are in the sample.
- Extraction takes *all* records for each selected episode — there is no count threshold that could trigger a conditional "try another episode" branch.
- The zero-record case is handled by inclusion-with-disclosure, not substitution — the one place a naive fallback could have smuggled in outcome-dependence (swap the episode if it has too few records) is explicitly rejected in §3 above, not merely left unaddressed.

## 5. What the sample does and does not prove

**Proves:** a reviewer can inspect real, representative per-tick A3-D decisions from the actual holdout run, evenly spread across the entire holdout index range, selected by a formula fixed before any holdout access — genuine transparency into real output, exactly as `docs/A3-DESIGN.md §22` intends the artifact to function.

**Does not prove, and no artifact produced from this sample may claim:** coverage of every `tick_type`, every gate-rejection path (R1–R8), or every `fallback_reason` value. That is structurally unreachable from any real A3-D holdout sample (§2 item 4 above) and remains the job of the **existing, independent synthetic-adversarial test suite** — `tests/test_gate_rules.py` (R1–R8, one triggering + one non-triggering proposal per rule), `tests/test_planner_fallback_ledger.py`, `tests/test_gate_rejection_fallback.py`, and `tests/test_a3_llm_forced_failure_parity.py` (the four verified `fallback_reason` paths). Those tests are unaffected by, and independent of, this ruling and this sample.

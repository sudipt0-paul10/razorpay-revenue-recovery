# DAY 10 — MONETARY INVOICE-VALUE RECOVERY

**Post-hoc descriptive analysis of already-sealed holdout artifacts; not a
pre-registered primary metric and not a new evaluation.**

**Status:** Day 10, single authorized analysis. It aggregates fields that
already exist inside the sealed `holdout` artifacts of run `4d45db461943`.
It does not modify, and has no authority to modify, `EVAL.md §7`'s
pre-registered criteria or the verdicts already recorded in `RESULTS.md`.
No arm, threshold, prompt, config, or comparator was changed. No split was
re-run. No simulator was invoked.

Reproduce with:

```bash
python scripts/day10_value.py
```

---

## 1. Scope, and the Day 9 boundary this stage crosses

This document answers one question: **how much invoice value, in rupees, did
each official arm actually recover on the frozen holdout?**

`docs/analysis/DAY9-NET-VALUE.md §1` and `§7` explicitly declined to compute
this. That stage's authorization (its rule 7) forbade deriving new statistics
from `results/holdout/4d45db461943/*/episode_results.jsonl`, so Day 9
substituted two registered *population-level* reference values for the value
of a marginal recovery and reported a bracketed break-even range instead:

> "the exact, arm-conditional expected value of a marginal invoice recovery
> is NOT available from anything this stage may legitimately use, and this
> document does not invent one." — `DAY9-NET-VALUE.md §5.1`

**Day 10 is separately and explicitly authorized to read those sealed
per-episode files.** That is the only difference between the two stages, and
it is recorded here so the apparent contradiction between `DAY9-NET-VALUE.md
§7` limitation 1 and this document is traceable to a stated change of
authorization rather than to a quietly relaxed boundary. Nothing else about
the Day 9 contamination rules is relaxed: no holdout index is re-drawn, no
new statistical test or confidence interval is constructed, and no DEV figure
appears anywhere below.

**What this document is not:**

- Not a new evaluation, and not a new success criterion. `EVAL.md §7`'s
  criteria are closed; A3-D's `RESULTS.md` verdict stands exactly as
  recorded.
- Not a rerun. `rrx.harness.splits.holdout_indices(authorized=True)` is never
  called; `scripts/day10_value.py` imports no `rrx` module at all.
- Not a rescue-side valuation. No cancellation-value or LTV parameter is
  registered anywhere in `configs/`, so none is used and none is invented
  (`DAY9-NET-VALUE.md §7` limitation 3 remains open and unchanged).
- Not a re-tuning, and not a basis for one.

## 2. Source artifacts and provenance

| Item | Value |
|---|---|
| Holdout run directory | `results/holdout/4d45db461943/` |
| Per-episode source (per arm) | `<arm>/episode_results.jsonl` |
| Published-metric cross-reference | `<arm>/metrics.json` |
| Integrity manifest | `SHA256SUMS` (21 artifacts) |
| Seal tag | `holdout-run-4d45db461943-sealed` → `2d451088ef5105b5075b5f4990803da5230e00bb` |
| Run commit (`manifest.json` `git_sha`) | `29e8cd394402f9fef1b32a7ed1ffaf69f474a572` |
| Spec version (`manifest.json`) | `eval-spec-v1.10` |
| Config hash (identical, all 5 arms) | `d1a8e016329de4095becb3b70662a3bb6b5f400c86e087df649f2054f8798866` |
| Master seed | `20260825` |
| Regime | `B` |
| Arm subdirectories | `a0`, `a1`, `a2_strengthened`, `a3_d`, `a4` |
| N per arm | 2,000 (10,000 episodes total) |
| Cost parameters | `configs/costs.yaml` |

**Seal verification, run before any episode data was read:** 21/21 artifacts
OK. `scripts/day10_value.py` recomputes every SHA-256 in `SHA256SUMS` itself
and exits non-zero, without aggregating anything, on a single mismatch.

### Fields actually used

The `episode_results.jsonl` schema is identical across all five arms
(verified: same key tuple on all 10,000 rows). Eight fields exist; this
analysis reads four:

| Field | Type | Use |
|---|---|---|
| `invoice_amount_inr` | `int` | invoice value at risk, and value recovered |
| `invoice_recovered` | `bool` | recovery indicator |
| `contacts_sent` | `int` | contact totals, cross-checked against `metrics.json` |
| `episode_index` | `int` | duplicate and pairing checks |

`subscription_rescued` is deliberately **not** monetised (§1). The remaining
fields (`opening_condition_key`, `wasted_attempts`,
`card_change_sent_for_insufficient_funds`) are not used.

## 3. Computed monetary results

**Total invoice value at risk: ₹64,66,221** — identical for every arm, which
is the expected consequence of common-random-number pairing (`EVAL.md §6`)
and is verified rather than assumed (§5).

| Arm | Invoice value at risk | Invoice value recovered | Value recovery rate | Incremental vs A0 |
|---|---:|---:|---:|---:|
| A0 | ₹64,66,221 | ₹23,19,477 | 0.3587 | — |
| A1 | ₹64,66,221 | ₹30,10,915 | 0.4656 | +₹6,91,438 |
| A2-strengthened | ₹64,66,221 | ₹30,49,789 | 0.4716 | +₹7,30,312 |
| **A3-D** | ₹64,66,221 | **₹28,67,109** | **0.4434** | **+₹5,47,632** |
| A4 (oracle reference) | ₹64,66,221 | ₹33,41,626 | 0.5168 | +₹10,22,149 |

A0 is the no-contact floor: the ₹23,19,477 it recovers is what Razorpay's own
auto-retry schedule collects with no merchant contact at all. The
"incremental vs A0" column is therefore the value attributable to the contact
policy itself, not to the retry engine. A4 is an oracle with full hidden-state
access and is **not** a deployable comparator (`EVAL.md §7`).

## 4. A3-D comparison

| | vs A1 | vs A2-strengthened |
|---|---:|---:|
| Recovered-value deficit (gross) | **−₹1,43,806** | **−₹1,82,680** |
| Marginal recoveries forfeited | 43 | 52 |
| Contacts saved | 907 | 755 |
| Contact-cost saving — cash only (₹0.115) | ₹104.31 | ₹86.83 |
| Contact-cost saving — effective (₹1.115) | ₹1,011.30 | ₹841.83 |
| Deficit ÷ effective saving | **142×** | **217×** |

The registered effective contact cost of ₹1.115 is the sum of two components
in `configs/costs.yaml`: a **CITE**-labelled WhatsApp utility price of ₹0.115
and an **ASSUMPTION**-labelled synthetic annoyance penalty of ₹1.00. Only the
first is a cash outflow. Both rows are shown because the distinction changes
the saving by an order of magnitude and does not change the conclusion at
either value: A3-D's restraint saved between ₹87 and ₹1,011 depending on which
component set is counted, against a forfeited invoice value of ₹1.44–₹1.83
lakh.

Stated in one line: **against A1, A3-D's restraint saved ₹1,011 in registered
contact cost and gave up ₹1,43,806 in recovered invoice value.**

No rupee value is attached to A3-D's subscription-rescue position (0.5085 vs
A1's 0.4890), because no rescue-value parameter is registered. The comparison
above is invoice-side only and is not a complete economic verdict on the arm.

### 4.1 Measured marginal-recovery value against the Day 9 bracket

Day 9 could not measure the value of a marginal recovery and bracketed it
between the registered median (₹2,000) and the lognormal population mean
(₹3,297.44). Those figures are now measurable:

| | vs A1 | vs A2-strengthened |
|---|---:|---:|
| Measured net value per forfeited recovery | ₹3,265.40 | ₹3,430.17 |
| Day 9 net reference range | ₹1,952.80 – ₹3,219.62 | ₹1,952.80 – ₹3,219.62 |
| Measured break-even contact cost | **₹154.81** | **₹236.25** |
| Day 9 bracketed break-even | ₹92.58 – ₹152.64 | ₹134.50 – ₹221.75 |
| Multiple of registered ₹1.115 | 139× | 212× |

Both measured break-even figures land **above** Day 9's bracketed upper bound
— ₹154.81 vs ₹152.64, and ₹236.25 vs ₹221.75. The reason is visible in §5's
rate comparison: the recoveries A3-D forfeited were worth modestly more than
the population mean invoice, so Day 9's population-level reference slightly
understated the deficit. Day 9's lognormal-mean **INFERENCE** was accurate to
within about 1.4% against A1 and about 6% against A2-strengthened.

**This strengthens, and does not revise, Day 9's conclusion.** The
contact-cost saving remains roughly two orders of magnitude short of covering
the forfeited recovery value under the registered cost model.

## 5. Cross-checks

All checks are enforced in `scripts/day10_value.py`; the script exits non-zero
rather than printing results if any of them fail.

| Check | Result |
|---|---|
| Seal verified before reading episode data | 21/21 SHA-256 OK |
| N per arm | 2,000 on all five arms |
| Duplicate `episode_index` values | none, any arm |
| `episode_index` vector identical across arms | yes |
| `invoice_amount_inr` vector identical across arms (CRN) | yes — byte-for-byte equal ordered vectors |
| Missing/null `invoice_amount_inr`, `invoice_recovered`, `contacts_sent` | none (10,000 rows, all `int`/`bool`) |
| Recomputed episode-count recovery rate vs sealed `metrics.json` | exact match, all five arms |
| Recomputed contact totals vs sealed `metrics.json` | exact match, all five arms |

### Value-weighted rate vs published episode-count rate

These are different quantities and are **not** forced to agree. `RESULTS.md
§4` publishes the episode-count rate; the value-weighted rate is new here.

| Arm | Value-weighted rate | Published count rate (`RESULTS.md §4`) | Delta |
|---|---:|---:|---:|
| A0 | 0.3587 | 0.3585 | +0.0002 |
| A1 | 0.4656 | 0.4640 | +0.0016 |
| A2-strengthened | 0.4716 | 0.4685 | +0.0031 |
| A3-D | 0.4434 | 0.4425 | +0.0009 |
| A4 | 0.5168 | 0.5245 | **−0.0077** |

Four arms show a small positive delta: the invoices they recover are, on
average, marginally larger than the population. **A4 is the exception and
runs the other way** — the oracle's extra recoveries skew toward *smaller*
invoices, so its rupee performance is slightly worse than its episode-count
performance suggests. A4 is a reference ceiling, not a comparator, so this
does not affect any published verdict; it is recorded because it is the one
place where the two rate definitions disagree in direction.

For A3-D specifically the delta is +0.0009 — the recovery deficit recorded in
`RESULTS.md` is **not** an artifact of invoice size. A3-D does not lose
because it forfeits unusually large or unusually small invoices; it loses
because it forfeits recoveries.

## 6. Limitations

1. **Descriptive, not inferential.** Every rupee figure above is a point
   estimate. No confidence interval is constructed on any monetary quantity.
   The underlying *rate* differences do carry pre-registered, already-
   published holdout CIs (`RESULTS.md §7`), and those CIs exclude zero in
   A3-D's unfavourable direction — but no new CI is computed here, and the
   ₹ figures must not be read as though one were.
2. **Gross of gateway fees in §3 and §4's headline rows.** The main table
   reports gross recovered invoice value. `configs/costs.yaml` registers a
   2.36% successful-capture fee (**CITE**); §4.1 applies it, §3 does not.
   Compare like with like when quoting these figures.
3. **The ₹1.115 effective contact cost is not a pure cash price.** ₹1.00 of
   it is a labelled synthetic annoyance **ASSUMPTION**, not an outflow. §4
   reports both the cash-only and effective figures for this reason.
4. **Invoice side only.** No monetary value is assigned to subscription
   rescue. `configs/costs.yaml` has no cancellation-value field, and
   `EVAL.md §3.3`'s cancellation-hazard mechanic is unimplemented in the
   simulator (`LIMITATIONS.md §3.4`). A complete economic verdict on A3-D is
   therefore still not available, and this document does not claim to
   provide one.
5. **Simulator-generated values.** Every rupee here is drawn from the frozen
   synthetic population (`configs/population.yaml`, lognormal, median ₹2,000,
   σ=1.0). These are not real merchant invoices and carry the same external-
   validity limits as every other number in this project (`LIMITATIONS.md
   §1`).
6. **Holdout-only.** No DEV figure appears in this document.
7. **The A4 sign reversal in §5 is reported, not explained.** Establishing
   *why* the oracle's recoveries skew small would require a per-episode
   analysis of the oracle's selection behaviour, which is outside this
   stage's scope.

## 7. What this changes

Nothing in `RESULTS.md`, and nothing in `EVAL.md`. A3-D's holdout verdict is
unchanged: criterion 2 failed, criteria 1 and 3 passed.

What it adds is the missing ₹ denomination of a result that was already
final, and the closure of `DAY9-NET-VALUE.md §7` limitations 1 and 2 — the
arm-conditional value of a marginal recovery, and the invoice-size
correlation Day 9 could not measure.

`README.md`, `RESULTS.md`, `LIMITATIONS.md`, `docs/PITCH.md` and
`ARCHITECTURE.md` are deliberately **not** updated by this stage. In
particular, `docs/PITCH.md` and `RESULTS.md §14.1` currently quote Day 9's
₹92.58–₹221.75 bracketed break-even range, which §4.1 shows to be modestly
low at both ends. Reconciling those documents with the measured figures is a
separate, subsequent decision.

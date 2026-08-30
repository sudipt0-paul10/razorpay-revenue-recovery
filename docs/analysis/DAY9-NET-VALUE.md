# DAY 9 — NET VALUE ANALYSIS

**Status:** Day 9, Stage 1 only. A post-hoc descriptive economic
re-expression of the already-sealed `holdout` result. Pre-declared in
`CHANGELOG.md` ("Day 9 Stage 1 — net-value / break-even analysis,
pre-declaration", committed `42ad563`) before this document was written.
Does not modify, does not have the power to modify, and is not a
substitute for `EVAL.md §7`'s pre-registered criteria or `RESULTS.md`'s
already-recorded verdicts.

---

## 1. Scope and contamination boundary

This document answers exactly one question: **under the already-registered
cost model (`configs/costs.yaml`), does A3-D's holdout contact reduction
economically compensate for its holdout recovery-rate deficit against its
`EVAL.md §7` comparator set?**

What this document is:
- Arithmetic performed on numbers already published in `RESULTS.md` and
  the sealed `results/holdout/4d45db461943/*/metrics.json` files.
- A re-expression in ₹ terms of a result that is already final.

What this document is **not**, and does not do:
- It does not rerun, replay, or re-access any `holdout` index.
  `rrx.harness.splits.holdout_indices(authorized=True)` is not called
  anywhere in producing this document.
- It does not compute a new statistical test, confidence interval, or
  p-value on holdout data. Every number below is either a published point
  estimate or simple arithmetic on published point estimates — not a new
  paired-bootstrap procedure.
- It does not open, read, or aggregate any `holdout` per-episode file
  (e.g. `results/holdout/4d45db461943/*/episode_results.jsonl`,
  `a3_d/ledger.jsonl`) to derive a new statistic (such as an
  arm-conditional mean recovered-invoice value). That data exists and is
  committed, but computing a new aggregate from it — one that has never
  itself been published as a metric — would mean deriving a new result
  from raw per-episode holdout data during a stage whose own rules forbid
  exactly that (rule 7 of this stage's authorization: "Do NOT inspect
  unpublished holdout per-episode data for the purpose of discovering a
  new result"). This boundary decision is recorded explicitly in §7 below,
  along with what it costs this analysis in precision.
- It does not change, tune, retune, or re-select A3-D, any comparator, or
  any cost parameter.
- It does not touch `EVAL.md`, `configs/costs.yaml`, `configs/population.yaml`,
  or any other locked file.

## 2. Registered economic assumptions

All values below are read verbatim from already-committed, locked
configuration and result files — none is invented for this analysis.

| Item | Value | Source |
|---|---:|---|
| WhatsApp per-message cost | ₹0.115 | `configs/costs.yaml:26` (`messaging.whatsapp.cost_inr`) |
| Annoyance penalty, per contact | ₹1.00 | `configs/costs.yaml:36` (`annoyance.per_contact_inr`) |
| **Effective contact cost (registered, as given)** | **₹1.115 / contact** | Sum of the two rows above, applied uniformly per contact per the terms of this stage's own authorization |
| Successful-capture processing fee | 2.36% (0.0236) | `configs/costs.yaml:10` (`gateway.successful_capture_fee_rate`) |
| Invoice-amount distribution | Lognormal, `median_inr=2000`, `sigma=1.0`, support `[100, 50000]` | `configs/population.yaml:39-46` |
| `net_recovered_formula` | `gross_recovered − successful_capture_processing_fee − failed_attempt_cost − contact_cost − annoyance_cost − llm_cost` | `configs/costs.yaml:54` |

**No LTV / cancellation-hazard value is registered anywhere in this
repository.** `configs/costs.yaml:585` region marks `cancellation_hazard,
remaining LTV` as "Regime A only" with no numeric field in the file itself;
`LIMITATIONS.md §3.4` and every sealed `metrics.json`'s
`unavailable_metrics.regime_a_net_value` entry state plainly that
`EVAL.md §3.3`'s cancellation-hazard mechanic "is not implemented anywhere
in `src/rrx/sim/`." This has a direct, binding consequence for §5 below:
**no monetary value can be attached to a subscription rescue.** Only
invoice recovery has a registered ₹ value path (the invoice amount itself,
net of the capture fee).

## 3. A3-D vs. comparator contact savings

**MEASURED** (published `RESULTS.md` §4 / `results/holdout/4d45db461943/*/metrics.json`
`total_contacts`), **ARITHMETIC RE-EXPRESSION** (the differences and
percentages):

| Comparator | Comparator contacts | A3-D contacts | Absolute savings | % reduction |
|---|---:|---:|---:|---:|
| A1 | 3,778 | 2,871 | **907** | **24.01%** |
| A2-strengthened | 3,626 | 2,871 | **755** | **20.82%** |

(907 = 3,778 − 2,871; 907 / 3,778 = 0.24007. 755 = 3,626 − 2,871; 755 / 3,626 = 0.20822.)

## 4. Recovery deficit

**MEASURED** (published rates, `RESULTS.md` §4), **ARITHMETIC RE-EXPRESSION**
(implied counts, since N=2,000 per arm on holdout — `RESULTS.md` §2).
Per this stage's own instruction, only the `EVAL.md §7` comparator-set
members are used for each metric (invoice recovery: A1 and
A2-strengthened; subscription rescue: A2-strengthened only).

**Invoice recovery:**

| Comparator | Comparator rate | A3-D rate | Rate deficit | Implied additional recoveries / 2,000 episodes |
|---|---:|---:|---:|---:|
| A1 | 0.4640 | 0.4425 | 0.0215 | **43** |
| A2-strengthened | 0.4685 | 0.4425 | 0.0260 | **52** |

(0.4640×2000=928 recovered under A1; 0.4425×2000=885 recovered under
A3-D; 928−885=43. 0.4685×2000=937 under A2-strengthened; 937−885=52.)

**Subscription rescue** (comparator set = {A2-strengthened} only):

| Comparator | Comparator rate | A3-D rate | Rate deficit | Implied additional rescues / 2,000 episodes |
|---|---:|---:|---:|---:|
| A2-strengthened | 0.5190 | 0.5085 | 0.0105 | **21** |

(0.5190×2000=1,038; 0.5085×2000=1,017; 1,038−1,017=21.)

*Not a comparator, informational only:* A3-D's subscription rescue rate
(0.5085) actually **exceeds** A1's (0.4890) by 39 rescues per 2,000
episodes. This is not part of any criterion-2 comparator set for this
metric (`RESULTS.md` §5: A1 is not in the rescue-rate comparator set) and
carries no weight in the break-even calculation below — noted only so a
reader does not mistake A3-D for uniformly worse than every arm on every
metric.

## 5. Break-even contact cost

### 5.1 What can be validly computed, and what cannot

Per this stage's own instruction: **the median invoice amount
(₹2,000, `configs/population.yaml:42`) is not automatically the mean.**
For a lognormal distribution the mean is `median × exp(σ²/2)`, strictly
greater than the median whenever `σ > 0`, and `configs/population.yaml`
registers `sigma: 1.0` — so the gap here is not small.

No published aggregate in this repository reports a mean or total
recovered-invoice value for any arm on `holdout` — `RESULTS.md` and every
sealed `metrics.json` report only rates and contact counts, not ₹ sums.
The one place invoice amounts exist per-episode is
`results/holdout/4d45db461943/*/episode_results.jsonl`, and per §1/§7 of
this document, deriving a new "mean recovered-invoice value" statistic
from that raw per-episode file is treated as out of bounds for this stage
(rule 7). **Consequently, the exact, arm-conditional expected value of a
marginal invoice recovery is NOT available from anything this stage may
legitimately use**, and this document does not invent one.

What **can** be validly computed, without touching per-episode data: the
*population-level* lognormal mean implied by the already-registered,
already-frozen distribution parameters (`median_inr=2000`, `sigma=1.0`).
This is a deterministic closed-form function of two numbers fixed before
any holdout run existed — not a new measurement, not a selection made
after seeing an outcome (rule 8), and not per-episode data. It is
presented below as an **INFERENCE**, clearly distinct from a **MEASURED**
figure, alongside the raw registered median as a second, explicitly-labeled
reference point — not because the median is being treated as the mean, but
because it is the one other registered number available, shown so the
reader can see how sensitive the conclusion is to which reference is used.

| Reference value | ₹ | Status | Source / derivation |
|---|---:|---|---|
| Registered median | 2,000 | **ASSUMPTION** (explicitly NOT the mean) | `configs/population.yaml:42` |
| Lognormal population mean | 3,297.44 | **INFERENCE** | `median × exp(σ²/2) = 2000 × exp(0.5) = 2000 × 1.648721...`, from `configs/population.yaml:40-43` (`dist: lognormal`, `median_inr: 2000`, `sigma: 1.0`) |

Net value per recovery, after the registered 2.36% capture fee
(`configs/costs.yaml:10`), **ARITHMETIC RE-EXPRESSION** of the two rows
above:

| Reference | Net ₹ per recovery = value × (1 − 0.0236) |
|---|---:|
| Median-based | 2,000 × 0.9764 = **1,952.80** |
| Lognormal-mean-based | 3,297.44 × 0.9764 = **3,219.62** |

### 5.2 Equation

Break-even per-contact cost `X` is the contact price at which A3-D's
contact-cost savings against a comparator exactly equal the net value of
the invoice recoveries A3-D forfeits relative to that comparator:

```
ΔContacts × X  =  ΔRecoveries × V

X = (ΔRecoveries × V) / ΔContacts
```

where `ΔContacts` = comparator's total contacts − A3-D's total contacts
(§3), `ΔRecoveries` = comparator's implied recovery count − A3-D's implied
recovery count (§4), and `V` = net ₹ value per recovery (§5.1).

**This equation applies to invoice recovery only.** No equivalent equation
is computed for subscription rescue — see §2's LTV note; there is no
registered `V` for a rescue.

### 5.3 Result

**ARITHMETIC RE-EXPRESSION**, using the two `V` reference points from §5.1:

| Comparator | ΔContacts | ΔRecoveries | Break-even X, median V | Break-even X, lognormal-mean V |
|---|---:|---:|---:|---:|
| A1 | 907 | 43 | (43 × 1,952.80) / 907 = **₹92.58** | (43 × 3,219.62) / 907 = **₹152.64** |
| A2-strengthened | 755 | 52 | (52 × 1,952.80) / 755 = **₹134.50** | (52 × 3,219.62) / 755 = **₹221.75** |

As a multiple of the registered ₹1.115/contact cost:

| Comparator | Multiple, median V | Multiple, lognormal-mean V |
|---|---:|---:|
| A1 | **83.0×** | **137.0×** |
| A2-strengthened | **120.7×** | **198.9×** |

## 6. Economic interpretation

**On invoice recovery**, the break-even contact cost is roughly two orders
of magnitude above the registered ₹1.115. Restated directly at the
registered cost (**ARITHMETIC RE-EXPRESSION**, same inputs as §5, net value
of switching *from* the comparator *to* A3-D, per 2,000-episode cohort):

| Comparator | V reference | Contact-savings value (ΔContacts × ₹1.115) | Lost-recovery value (ΔRecoveries × V) | Net value of A3-D vs. comparator |
|---|---|---:|---:|---:|
| A1 | median | ₹1,011.30 | ₹83,970.40 | **−₹82,959.10** |
| A1 | lognormal-mean | ₹1,011.30 | ₹138,443.78 | **−₹137,432.48** |
| A2-strengthened | median | ₹841.83 | ₹101,545.60 | **−₹100,703.78** |
| A2-strengthened | lognormal-mean | ₹841.83 | ₹167,420.39 | **−₹166,578.57** |

Under every combination tested — either comparator, either invoice-value
reference — **A3-D's contact savings recover under 1.3% of the value its
recovery-rate deficit forfeits.** The contact-cost side of this trade is
economically negligible next to the recovery-rate side, given the
registered cost model. This is not a close call: the gap between the
registered cost (₹1.115) and the computed break-even cost (₹92.58–₹221.75)
spans roughly 83× to 199×, which is far larger than the uncertainty
introduced by not knowing the exact arm-conditional mean invoice value
(§5.1's two references only differ from each other by ~1.65×, not
~100×).

**On subscription rescue**, no monetary interpretation is possible under
the registered cost model — see §2 and §7.

## 7. Limitations

1. **No arm-conditional mean recovered-invoice value is available from
   any published aggregate.** `RESULTS.md` and every sealed `metrics.json`
   report only rates and contact counts. The precise figure exists only
   inside `episode_results.jsonl` per-episode files, and deriving a new
   statistic from those files was ruled out of scope for this stage (§1).
   §5 substitutes two labeled reference values (registered median;
   lognormal population mean, mechanically derived from already-frozen
   config) instead of inventing or silently assuming either is the true
   figure.
2. **The two reference values in §5.1 are population-level, not
   recovered-episode-conditional.** If invoice amount correlates with
   which episodes get recovered under a given arm (plausible — larger
   invoices might see different retry/engagement dynamics), the true
   mean recovered-invoice value could differ from both reference points
   in either direction. This document does not, and under its own
   contamination boundary cannot, measure that correlation.
3. **No LTV or cancellation-hazard value is registered anywhere in this
   project**, so no economic break-even exists for subscription rescue.
   `configs/costs.yaml` has no field for it; `EVAL.md §3.3`'s
   cancellation-hazard mechanic is unimplemented in the simulator itself
   (`LIMITATIONS.md §3.4`). This is a pre-existing gap in the registered
   cost model, not something this analysis introduces or could close.
4. **The ₹1.115 effective contact cost is applied uniformly to every
   arm's contacts**, per this stage's own pre-declared assumption. This
   repository's baselines are not all confirmed to use the WhatsApp
   channel specifically for cost purposes; this document does not
   investigate or challenge that assumption, only reports it as given.
5. **This is holdout-only, point-estimate arithmetic — no confidence
   interval is computed or implied on any ₹ figure above.** The rate
   deficits underlying §4/§5/§6 do carry pre-registered, already-published
   holdout CIs (`RESULTS.md` §7: e.g. A3-D vs. A2-strengthened invoice
   recovery diff 95% CI [−0.0340, −0.0185]) — i.e., the *rate* difference
   driving this entire analysis is not merely a point estimate, it is
   already known to exclude zero. But no new CI is constructed on the
   ₹-denominated quantities themselves (contact-savings value,
   lost-recovery value, break-even X); doing so would require a paired
   bootstrap over per-episode monetary outcomes, which is exactly the
   per-episode holdout computation this stage's contamination rules
   place out of scope (§1).
6. **No DEV-split figures appear anywhere in this document.** Every rate,
   contact count, and cost figure above is holdout-only, sourced from
   `RESULTS.md` and `results/holdout/4d45db461943/`. Per this stage's
   explicit instruction, DEV and holdout are not mixed here.

## 8. World A / World B verdict

**World A (registered cost model, as actually specified in `configs/costs.yaml`):
A3-D is economically unfavorable relative to both invoice-recovery
comparators (A1, A2-strengthened), by a wide margin.** The break-even
contact cost (₹92.58–₹221.75, depending on which invoice-value reference
is used) exceeds the registered cost (₹1.115) by roughly 83× to 199×. This
conclusion is robust to the uncertainty flagged in §7 items 1–2: closing
an 83×–199× gap would require the unmeasured recovered-invoice-value
correlation to be implausibly large, far beyond what a ~1.65× spread
between the median and lognormal-mean references suggests is plausible.

**No World B is constructed here.** This stage's instructions are explicit
that a World A/World B conclusion should not be forced if the available
published aggregates are insufficient — and for **subscription rescue**,
they are: with no registered LTV/cancellation-hazard value anywhere in
this project's cost model, there is no economically valid "World B" to
compute for that metric, only the qualitative recovery-deficit fact
already stated in §4 (21 fewer rescues per 2,000 episodes vs.
A2-strengthened, alongside 907/755 fewer contacts vs. A1/A2-strengthened
respectively — both facts reported, neither monetized).

**Summary sentence:** under the cost model this project has actually
registered, A3-D's reduction in contacts does not come close to
compensating for its reduction in invoice recovery on holdout; no
equivalent statement can be made for subscription rescue because this
project's registered cost model does not price a subscription rescue at
all.

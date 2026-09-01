# PITCH.md — RR-X: Subscription Recovery Orchestration Agent

*Razorpay AI Buildathon, Track 03 — AI Revenue Recovery*

**This document is the final 5-minute pitch/demo script.** It supersedes the previous longer prose pitch — the same facts, restructured for spoken delivery. Every number below is cross-checked against `RESULTS.md` (frozen holdout) or `docs/analysis/DAY9-*.md` (post-hoc diagnostics) at the citation given. 696 spoken words ≈ 4:58 at a conservative 140 words/minute, ≈4:38 at a brisker 150 — under the 5-minute cap either way, but with only ~2s of margin at 140 wpm: rehearse to time. Timestamps below are cumulative estimates at 140 wpm. Presenter cues are in `[brackets]` and are not spoken.

**The story, in one line:** we built a constrained recovery agent, froze the evaluation before looking at holdout, found the frozen policy lost on its primary metric, diagnosed exactly why, quantified the economic cost, and used dev-only experiments to show the loss was a tuning problem rather than a ceiling — without touching the sealed holdout to "fix" the number.

---

## Script

### 1. Hook / Problem — `0:00–0:26`

> When a subscription payment fails, Razorpay already retries the charge automatically — the merchant can't touch that. What the merchant *does* control is whether to contact the customer, and when to stop. Contact costs money and risks annoying someone into cancelling outright. Contacting forever isn't a strategy — it's noise. The real problem is deciding when contact is actually worth it.

### 2. What We Built — `0:26–0:56`

`[cue: show docs/architecture/revenue-recovery-architecture.svg]`

> We built a simulator, an evaluation harness, and a recovery agent. Each tick, the agent sees an `EpisodeView` — decline reason, retry status, contact history, nothing hidden. It proposes an action; a safety gate checks eight hard rules — no contacting cancelled subscriptions, no wrong remedy, no exceeding budget — before an executor acts and every decision is ledger-recorded. Policy proposes, gate validates, executor acts, ledger records. Safety isn't optional here.

### 3. AI / LLM Component — `0:56–1:18`

> We also built and tuned an LLM planner, A3-LLM, on GPT-5-mini — real API calls, real ledgers, six configurations at 500 episodes each. But the policy we froze and evaluated, A3-D, is fully deterministic — a sixteen-rule table, no network call. A3-LLM never touched holdout. Zero claim of LLM holdout performance.

### 4. Evaluation Discipline — `1:18–1:49`

> Before touching holdout data, we froze the entire evaluation contract — criteria, comparator rules, statistics — all tagged in git. Dev and holdout use separate seed ranges; holdout is single-use, checksummed and sealed the moment it runs. Every arm sees an identical simulated world through common-random-number pairing, so differences come from decisions, not luck. We track recovery rate, rescue rate, contacts, and eight safety invariants. No tuning after that seal — ever.

### 5. Results — `1:49–2:19`

`[cue: show the results table from RESULTS.md]`

| Arm | Invoice recovery | Subscription rescue | Contacts |
| --- | ---: | ---: | ---: |
| A0 | 0.3585 | 0.3920 | 0 |
| A1 | 0.4640 | 0.4890 | 3,778 |
| A2-strengthened | 0.4685 | 0.5190 | 3,626 |
| **A3-D** | **0.4425** | **0.5085** | **2,871** |
| A4 (oracle) | 0.5245 | 0.5445 | 3,076 |

> Here's the frozen holdout result. A3-D used 2,871 contacts — far fewer than A1's 3,778 or A2-strengthened's 3,626. But its invoice recovery, 0.4425, and rescue, 0.5085, both came in below the comparator set, with confidence intervals excluding zero, unfavorably. Criterion 2 — beat the comparators — failed. Criterion 1, safety, passed clean. Criterion 3, contact discipline, passed too. We're not spinning this: on the metric that matters most, A3-D lost.

### 6. What Caused the Failure — `2:19–3:04`

`[cue: show docs/analysis/DAY9-DECOMPOSITION.md, the 59/59 finding]`

> So we dug in. Against A2-strengthened, all 59 of its extra recoveries trace to one mechanism: A3-D withholding its day-three contact after two unengaged touchpoints — logged as `no_engagement_restraint`. Against A1, the same mechanism explains 41 of 47 losses. It's not STOP — zero of A3-D's 311 holdout STOP actions overlap with a lost recovery. It's not wrong remedies — every contact A3-D actually sent matched the correct remedy, 100 percent. We also directly ruled out cancelled-at-open episodes as contamination. The agent didn't give up — the specific restraint rule, skip the second contact if nobody's engaged yet, was tuned too aggressively for this tradeoff.

### 7. Economic Interpretation — `3:04–3:40`

`[cue: post-hoc descriptive analysis of sealed holdout artifacts (docs/analysis/DAY10-VALUE.md) — not a pre-registered metric, no CI]`

> Under our registered cost model, A3-D saved 907 contacts versus A1 at ₹1.115 each — and only eleven paise of that is a cited price, the rest a labelled annoyance assumption. Reading the sealed episode files afterwards, we can price that restraint: about ₹1,000 saved against ₹1.44 lakh of invoice value given up. Break-even needs ₹155 per contact against A1, ₹236 against A2-strengthened — over a hundred times the registered cost. Post-hoc descriptive, not a pre-registered metric. No rescue-side ₹ number — none is registered.

### 8. What We Learned / DEV Frontier — `3:40–4:11`

`[cue: emphasize DEV-ONLY, not a holdout claim]`

> This failure doesn't mean the architecture is broken. On dev data only, never holdout, we swept the restraint threshold and found a less cautious setting that hit 0.4920 recovery and 0.5445 rescue at 3,710 contacts — beating A1 outright on every axis. That's evidence of parameter sensitivity, not a structural ceiling. We never ran it on holdout, so we make zero claim it's validated. A deliberate line we chose not to cross.

### 9. Demo Sequence — `4:11–4:36`

`[cue: open results/audit_sample/a3d_holdout_ledger_sample.jsonl — the committed, checksum-sealed audit excerpt]`

> Episode `holdout-9000`, decline reason card-expired. Day zero: policy proposes a card-change contact, rule R-12, gate accepts, executor sends it, ledger logs it. Days one and two: no engagement, so the withhold rule fires — WAIT, rule R-16. Day three: the customer engaged, A3-D sends its second contact. All four decisions sit in that checksum-sealed file right now.

### 10. Closing — `4:36–4:58`

> Revenue recovery isn't a retry problem — it's a constrained decision problem, where value, cost, timing, safety, and auditability all interact. We preserved the frozen result, diagnosed the failure instead of hiding it. The next step is validating a less aggressive restraint policy — under a fresh, pre-registered evaluation, not this one.

---

## Demo artifacts (all pre-existing, none rerun for this pitch)

- **Architecture diagram:** `docs/architecture/revenue-recovery-architecture.svg` (Stage 8A) — for section 2.
- **Results table + criterion verdicts:** `RESULTS.md §4`, `§3A` — for section 5.
- **Seal / integrity check** (optional live command, read-only, does not rerun holdout): `sha256sum -c results/holdout/4d45db461943/SHA256SUMS`.
- **Mechanism finding:** `docs/analysis/DAY9-DECOMPOSITION.md §4–§5`, `results/day9_decomposition/decomposition_a2_strengthened.json` — for section 6.
- **Break-even + ₹-recovered figures:** `docs/analysis/DAY10-VALUE.md §4`, `§4.1` (measured; supersedes the earlier bracketed estimate in `docs/analysis/DAY9-NET-VALUE.md §5`, which is retained as historical context) — for section 7.
- **Dev-only frontier:** `docs/analysis/DAY9-FRONTIER.md §5` — for section 8.
- **Ledger walkthrough:** `results/audit_sample/a3d_holdout_ledger_sample.jsonl`, episode `holdout-9000` (first 4 records) — for section 9.

## Source citations (not spoken — for presenter Q&A backup)

| Claim | Exact source |
| --- | --- |
| Holdout table (A0–A4 rates/contacts) | `RESULTS.md §4` |
| Criterion 1/2/3 verdicts | `RESULTS.md §3A` |
| A3-D vs. A1/A2-strengthened CIs | `RESULTS.md §7` |
| GPT-C1–C6, N=500 each, real ledger evidence | `results/tuning_log.md`; `docs/analysis/DAY9-BAR-COMPLIANCE.md §8` |
| A3-LLM excluded from holdout | `EVAL.md §7.1` item A |
| 59/59 A2-strengthened deficit episodes; 41/47 A1 | `docs/analysis/DAY9-DECOMPOSITION.md §6` (Stage 2 counts) and Stage 3 §5 (rule attribution); summarized in `RESULTS.md §14.2–§14.3` |
| 0/311 STOP overlap | `docs/analysis/DAY9-DECOMPOSITION.md §9` |
| 100% remedy match | `docs/analysis/DAY9-DECOMPOSITION.md`, Stage 3 §3 |
| Cancelled-at-open ruled out | `docs/analysis/DAY9-DECOMPOSITION.md`, Stage 3 §6 (EVAL §8 item 8 verification) |
| 907 / 755 contacts saved; ₹1.115 registered effective cost = ₹0.115 **CITE** WhatsApp price (only cash component) + ₹1.00 **ASSUMPTION** annoyance penalty | `docs/analysis/DAY9-NET-VALUE.md §3`; `configs/costs.yaml` |
| Measured break-even ₹154.81 (vs A1) / ₹236.25 (vs A2-strengthened); ₹1,43,806 invoice value forfeited vs A1; ₹104.31 cash / ₹1,011.30 effective contact saving | `docs/analysis/DAY10-VALUE.md §4`, `§4.1` |
| Day 9's ₹92.58–221.75 bracket is the *earlier* estimate, superseded by the measured Day 10 values | `docs/analysis/DAY9-NET-VALUE.md §5`; `RESULTS.md §14.1`; `CHANGELOG.md` (Day 10 entry) |
| Threshold≥3 dev result (0.4920 / 0.5445 / 3,710), dev-only, not holdout-validated | `docs/analysis/DAY9-FRONTIER.md §5, §10` |

## What this script deliberately does not claim

- A3-D did not win criterion 2 on holdout. This script does not say it did.
- A3-LLM was not run on holdout, and no LLM holdout uplift is claimed.
- Threshold≥3 is dev-only exploratory evidence, not a validated or shipped policy — no "A3.1" exists.
- The ₹ figures are a **post-hoc descriptive aggregation** of already-sealed holdout artifacts (`docs/analysis/DAY10-VALUE.md`), authorized and recorded in `CHANGELOG.md`. They are **not** a pre-registered metric, carry **no confidence interval**, and do **not** revise the criterion 2 FAIL verdict. They are invoice-side only — no rescue-side ₹ value is claimed, because none is registered.
- No sensitivity-sweep completeness is claimed (`results/sensitivity.md` remains 0/26 — out of scope for this pitch, disclosed in `LIMITATIONS.md`).

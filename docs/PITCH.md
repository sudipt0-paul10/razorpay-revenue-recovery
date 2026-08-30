# PITCH.md — RR-X: Subscription Recovery Orchestration Agent

*Razorpay AI Buildathon, Track 03 — AI Revenue Recovery*

---

## 1. One-sentence hook

When a subscription payment fails, Razorpay already retries the charge automatically on a fixed schedule — the only open question is whether *contacting the customer* helps or just annoys them, and we built a rigorously pre-registered evaluation to answer that question honestly, including when the answer is "not yet."

## 2. Problem

When a customer's subscription payment fails, Razorpay's own systems retry the charge automatically, on a fixed schedule the merchant cannot control or trigger (`EVAL.md §1.1`). What the merchant *can* still do is decide **whether to contact the customer, when, on which channel, with which remedy — and when to stop** (`EVAL.md §1.2`). Get this wrong in one direction and you contact customers with the wrong remedy (prompting a card update for a balance problem helps nobody); get it wrong in the other direction and over-contacting risks the customer cancelling outright, which forfeits not just the one invoice but the subscription's entire remaining lifetime. There are two genuinely different outcomes worth recovering, and they are not the same thing (`EVAL.md §1.3`):

- **Invoice recovery** — the specific failed charge gets paid.
- **Subscription rescue** — the subscription itself returns to `active`, even if that one invoice is lost for good.

## 3. Solution

We built a recovery agent that decides, per customer per day, whether to send a contact, which of two remedies to send (a card-change prompt or a top-up reminder), or to wait — under a fixed contact budget shared by every arm we tested. The core design bet is **restraint**: contacting a customer isn't free (annoyance risk, cancellation hazard), so an agent that recovers the same number of invoices with fewer, better-targeted contacts is doing something a naive "contact everyone, twice" policy cannot. Restraint by itself isn't the win condition, though — it only matters if it also produces *more* invoices recovered and subscriptions rescued, at equal or lower contact cost. That is exactly what we pre-registered as the bar to clear, and it is exactly the number we report honestly below.

## 4. How it works

```
simulator → episode → agent → decision → recovery/contact → outcome
```

A synthetic **simulator** generates a population of failed-payment episodes from a frozen configuration — no real customer or merchant data anywhere in this project. Each **episode** starts with a subscription entering `pending` after a failed auto-charge, carrying hidden ("latent") state — like whether the card is actually broken, or funds are just temporarily short — that the **agent** never sees directly. Instead, the agent observes an `EpisodeView`: the subscription's declared failure reason, days since failure, auto-retry status, and its own contact history so far. From that, it makes a **decision**: contact now (with a specific remedy), wait, or stop. If it contacts, that becomes a **recovery/contact** event in the simulated world, which may or may not resolve the underlying problem depending on what's actually wrong. At the end of a 30-day window, every episode produces an **outcome**: did the invoice get paid, and did the subscription survive.

## 5. What we tested

Five arms, run over the identical episodes, the identical simulated worlds, and the identical 3-contact budget, so any difference between them is attributable to decision quality, not luck or a bigger budget:

| Arm | What it does |
|---|---|
| **A0** | Does nothing — the floor. Razorpay's own automatic retry and failure email still happen. |
| **A1** | Naive dunning: the same two contacts to every customer, always the same remedy, no judgment at all. |
| **A2-strengthened** | A competent, condition-aware fixed rulebook — the strongest non-agent baseline we built. |
| **A3-D** | Our deterministic recovery agent — a 16-rule decision table that reads the observable episode state and adapts. |
| **A4** | An oracle with full hidden-state visibility — **not deployable, not a target** — purely a reference for "how much headroom exists at all." |

The whole comparison — which arms count, which metrics matter, what statistical test decides a win, what "beating the baseline" even means when two baselines are statistically tied — was written down and frozen (`eval-spec-v1.10`) **before** the one holdout run that would judge it. That is the entire point: a number nobody can accuse of being cherry-picked after the fact, because the rule for reading it was fixed first.

## 6. Experimental rigor

- **Dev vs. holdout:** all tuning and development happened on a `dev` split (seeds 1000–2999); the `holdout` split (seeds 9000–10999) was never touched until one single, authorized, logged run.
- **Frozen contract:** `eval-spec-v1.10` — metrics, comparator rule, and success criteria were locked before that holdout run, tagged and committed.
- **Scale:** 2,000 episodes per arm, 5 arms, **10,000 total holdout episodes**, exact index range 9,000–10,999 verified with zero duplicates, gaps, or extras.
- **Statistics:** every comparison is a paired bootstrap (10,000 resamples, 95% confidence intervals) on common-random-number-paired episodes — not a raw point-estimate eyeball comparison.
- **Sealing:** every holdout artifact is checksummed (`SHA256SUMS`) and anchored by an immutable git tag (`holdout-run-4d45db461943-sealed`) *before* anyone looked at the numbers, so the result can't have been touched after the fact.

## 7. The result — reported honestly

**A3-D failed the pre-registered success criteria on holdout.**

| Arm | Invoice recovery rate | Subscription rescue rate | Total contacts |
|---|---:|---:|---:|
| A0 (floor) | 0.3585 | 0.3920 | 0 |
| A1 (naive) | 0.4640 | 0.4890 | 3,778 |
| A2-strengthened (best non-agent baseline) | 0.4685 | 0.5190 | 3,626 |
| **A3-D (our agent)** | **0.4425** | **0.5085** | **2,871** |
| A4 (oracle, reference only) | 0.5245 | 0.5445 | 3,076 |

On **both** primary metrics, A3-D scored **significantly below** its comparator set, not just short of beating it:

- Invoice recovery: A3-D vs. A1, diff = −0.0215, 95% CI [−0.0315, −0.0115]; A3-D vs. A2-strengthened, diff = −0.0260, 95% CI [−0.0340, −0.0185].
- Subscription rescue: A3-D vs. A2-strengthened, diff = −0.0105, 95% CI [−0.0180, −0.0030].

Both confidence intervals exclude zero — in A3-D's unfavorable direction. This is not a near-miss dressed up as a win.

## 8. What we learned

**A3-D achieved genuine contact restraint but did not translate that restraint into superior recovery or rescue performance.** It used fewer total contacts than every comparator arm and had the best contacts-per-outcome ratio of any contacting arm — the discipline mechanism worked exactly as designed (criterion 3 passes cleanly on both metrics). But restraint alone isn't the goal; it has to convert into *more* recoveries and rescues at that lower cost, and on this holdout run it didn't. The gap between A3-D and the oracle (A4) shows real headroom exists — A4 recovers more on both metrics using a comparable budget — which tells us the ceiling isn't the problem; A3-D's specific 16-rule decision table, as currently written, is. That is a concrete, falsifiable, actionable finding — exactly what a pre-registered evaluation is supposed to produce, win or lose.

## 9. Demo script

A short, honest, five-minute walkthrough:

1. **Show the frozen contract.** Open `EVAL.md §7` — point at the five pre-registered criteria and the comparator/tie-set rule, written before any holdout number existed. *Say:* "This is the rulebook, and it was locked before we ran the test that judges us against it."
2. **Show the seal.** Run `git show holdout-run-4d45db461943-sealed --no-patch` and open `results/holdout/4d45db461943/SHA256SUMS`. *Say:* "Every one of these 10,000 episodes' outputs is checksummed and tagged before anyone read a single number."
3. **Show the analysis code, not a spreadsheet.** Open `src/rrx/eval/holdout_analysis.py`'s `analyze_holdout()` — the same function that produced every number in `RESULTS.md`. *Say:* "This isn't a number we typed in — it's the output of code that recomputes everything from the raw per-episode files and cross-checks it against the committed aggregate."
4. **Show the result table in `RESULTS.md`.** *Say:* "A3-D lost. Here's the confidence interval that proves it's a real loss, not noise." Point at the negative, zero-excluding CIs.
5. **Close on the restraint finding.** Point at A3-D's contact totals vs. A2-strengthened's. *Say:* "It learned to hold back — it just didn't yet learn to hold back on the right episodes."

**Expected audience takeaway:** this team built an evaluation methodology rigorous enough to trust a "no" from, and reported the "no" instead of re-running until it said "yes."

## 10. Closing

The headline result is a loss, and we're not going to pretend otherwise. What we're presenting instead is the harness that made that loss trustworthy: a frozen contract, a single-use holdout, a sealed and checksummed artifact trail, and a statistical test that would have been just as willing to say "yes" if the evidence supported it. A3-D didn't clear the bar this time — but we now know exactly where it fell short, by how much, with what confidence, and why (restraint without better targeting). That is a stronger foundation to iterate from than an unfalsifiable win would have been, and it is not a claim that this system is ready for production — it is a claim that we now have an honest, reproducible way to find out when it is.

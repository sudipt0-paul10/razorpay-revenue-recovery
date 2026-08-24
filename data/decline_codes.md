# Razorpay Payment Decline / Recovery Classification

**Sources retrieved and verified:** 25 August 2026
**Machine-readable source of truth:** `data/decline_codes.yaml` — `tests/test_decline_codes_sync.py` asserts this file agrees with it.

---

## 0. What is documentation and what is ours

The single most important property of this file: **no classification, backoff, cap or action below is prescribed by Razorpay.** Razorpay documents what failed and what a merchant might do about it. Everything else is our policy.

Each rule therefore carries a `basis` field:

| `basis` | Meaning |
|---|---|
| `doc_supported` | Razorpay's documented next step directly supports this action |
| `project_inference` | Our reasoning from the documented *mechanism*, not from a documented recommendation |
| `fail_safe` | The docs are insufficient to decide; we take the conservative branch |
| `project_safety_policy` | We deliberately do **not** follow the documented recommendation. Rationale required. |
| `swept` | We could not settle it; it is a `[MODEL]` parameter resolved by `results/sensitivity.md` |

Field-level provenance:

- `doc_description` — `[CITE]`, from the linked page
- `classification` (`context`, `retry_class`, `resolution`, `agent_action`) — **project policy**
- `timing` (`backoff_hours`, `max_attempts`) — **`[ASSUMPTION]`, always.** No backoff in this repo comes from Razorpay.

---

## 1. Classification scheme

**`retry_class`** — can a retry of the same instrument, unattended, succeed?

`RETRY_TIMED` (yes, after a backoff) · `NO_RETRY` (not without a material change) · `UNVERIFIED` (resolves to `NO_RETRY`)

**`resolution`** — `NONE_NEEDED` · `CUSTOMER_ACTION` · `MERCHANT_ESCALATION`

**`context`** — `unattended_capable` (can occur on a mandate debit) · `attended_only` (checkout only; **excluded from the cohort** — see §2)

**`agent_action`** — the one action the gate permits. Anything else is rejected and logged.

### Fail-safe defaults `[INVARIANT]` — enforced in `gates/decline_class.py`

1. An unrecognised code resolves to `NO_RETRY` + `MERCHANT_ESCALATION`, action `escalate_unknown_failure`. **It does not assume the instrument needs updating** — we do not know that, and telling a customer to update a working card because we hit an unmapped code is both wrong and confusing.
2. `UNVERIFIED` behaves as `NO_RETRY` until a source link exists.
3. An unrecognised `source` value fails safe: the conservative sub-case wins.
4. Where sub-cases exist and `source`/`step` do not disambiguate, the least-retryable sub-case wins.

`NO_RETRY` does not mean the money is unrecoverable. It means the agent must not retry the same failing condition; recovery goes through a contact channel or an escalation.

---

## 2. Cohort scope — attended-only codes

Our episode is an **unattended mandate/subscription debit**. No customer is at a keyboard. Codes describing a customer failing to complete an interactive checkout therefore cannot occur, and the simulator must not emit them (`tests/test_no_attended_codes.py`).

Excluded as `attended_only`: `authentication_failed`, `incorrect_cvv`, `payment_timed_out` (customer sub-case), `payment_cancelled` (customer sub-case), `payment_collect_request_expired`.

**`[PROJECT ASSUMPTION]`.** Razorpay does not classify its codes by attendedness. This is our inference from the mechanics of an unattended debit, and it is a scope decision, not a documented fact. If the project later covers checkout recovery, these codes come back in.

---

## 3. Sources

| # | Page | URL | Status |
|---|---|---|---|
| 1 | List of Payment Errors | https://razorpay.com/docs/errors/payments/list/ | ❌ **JS-rendered; not machine-readable. Verify manually.** |
| 2 | Cards Error Codes | https://razorpay.com/docs/errors/payments/cards/ | ✅ 17 entries verified 25 Aug 2026 |
| 3 | UPI Error Codes | https://razorpay.com/docs/errors/payments/upi/ | ✅ 11 entries verified 25 Aug 2026 |
| 4 | Payment Method Error Parameters | https://razorpay.com/docs/errors/payments/payment-methods-error-parameters/ | ⚠️ **Cards** `source` values verified; UPI tab did not render |

Snapshots of pages 2–4 as retrieved are committed under `data/sources/`.

### 3.1 `source` routing

Verified card `source` values `[CITE]`: `customer`, `business`, `internal`, `gateway`, `issuer_bank`.

| `source` | Routing | Basis |
|---|---|---|
| `issuer_bank` | Needs `reason` to disambiguate; conservative fallback | `project_inference` |
| `gateway`, `internal` | Razorpay-side, transient by default | `project_inference` |
| `customer` | Usually `CUSTOMER_ACTION`, usually `attended_only` | `project_inference` |
| `business` | Our own integration error → **excluded from cohort** | `[PROJECT ASSUMPTION]` — a design decision about what counts as a recovery episode, not a Razorpay statement |
| *anything else* | Fail safe (rule 3) | `[INVARIANT]` |

**Open research item — UPI `source` values are NOT verified.** The UPI tab on page 4 did not render. Values sometimes cited elsewhere (`customer_psp`, `network`, `beneficiary_bank`) are **not** entered here, because we have not confirmed them. Confirm in a browser and add, or leave UPI routing on the fail-safe path. Do not add plausible-looking enum values to the source of truth.

### 3.2 `step` mappings — open, not blocking

The gate keys on `(code, source, step)`. The `step` enum is in a tab on page 4 that did not render and is unverified.

**Shipped behaviour until resolved:** sub-case codes route on `source` alone and fall through to the conservative sub-case (rule 4). This is correct-by-construction, only less precise. Sub-case codes are ~9% of the modelled mix, so this does not block `sim-v1` — but the fallback is documented shipped behaviour, not a silent gap, and `results/` must report how often it fired.

---

## 4. Card failures (source 2)

Timing columns are `[ASSUMPTION]` throughout.

| Code | Razorpay's documented description | retry_class | Resolution | basis | Backoff / cap | Action |
|---|---|---|---|---|---|---|
| `insufficient_funds` | Account did not have enough funds | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` — docs advise ensuring adequate balance; they do **not** recommend retrying. Ours is an inference that a balance condition changes over time. | 24h / 3 | `retry_payment` |
| `bank_technical_error` | Downtime on the customer's bank | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` — docs recommend a different bank and the Downtime API, not a retry. Ours infers transience from "downtime". | 6h / 3 | `retry_payment` |
| `gateway_technical_error` | Downtime on Razorpay's partner bank | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` — **the card page recommends multi-terminal routing and never mentions retrying.** Note this differs from the UPI page (§6). | 6h / 3 | `retry_payment` |
| `transaction_limit_exceeded` | Maximum transaction limit on the card reached **for the day**; docs recommend a different card or method | **`swept`** | see §5 | `swept` | see §5 | see §5 |
| `card_expired` | Card is expired | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_update_instrument` |
| `card_not_enrolled` | Card not activated/enabled for online transactions | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_update_instrument` |
| `card_disabled_for_online_payments` | *Equivalent documented description* | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_update_instrument` |
| `debit_instrument_inactive` | *Equivalent documented description* | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_update_instrument` |
| `debit_instrument_blocked` | Card blocked, by the customer or their bank | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_update_instrument` |
| `card_declined` | Declined by the customer's bank; **Razorpay states it may not have the specific reason** | `NO_RETRY` | `CUSTOMER_ACTION` | `fail_safe` | — | `contact_update_instrument` |
| `payment_failed` | *Equivalent documented description* | `NO_RETRY` | `CUSTOMER_ACTION` | `fail_safe` | — | `contact_update_instrument` |
| `payment_risk_check_failed` | Bank declined, citing it as fraudulent | `NO_RETRY` | `MERCHANT_ESCALATION` | `project_safety_policy` | — | `stop_episode` — see §7 |

**Aliases.** `card_not_enrolled`, `card_disabled_for_online_payments` and `debit_instrument_inactive` carry equivalent descriptions in the docs but are **three distinct codes that Razorpay emits separately**. They are stored as separate entries, not collapsed, and the simulator emits all three so the agent cannot key on one string.

**Attended-only, excluded from cohort (§2):** `payment_timed_out`, `payment_cancelled` (customer sub-case), `authentication_failed`, `incorrect_cvv`.

**`payment_cancelled` — bank downtime sub-case** *is* `unattended_capable`: `RETRY_TIMED`, 6h / 3, `project_inference`.

---

## 5. `transaction_limit_exceeded` — an open disagreement, resolved by measurement

Razorpay documents a **daily** limit and recommends a different card or payment method.

Two defensible readings:

**P1 — `NO_RETRY` + contact.** Follow the documented recommendation literally. Never retry the same card.

**P2 — one retry after reset, then contact.** The documented *mechanism* is a daily limit, which resets. Razorpay's "use a different card" recommendation is written for attended checkout; **an unattended mandate debit is bound to one instrument and cannot switch cards**, so the documented remedy is unavailable to us. Retrying past the reset carries no compliance risk — a daily limit is not a fraud signal or a permanent condition.

We did not settle this. It is a `[MODEL]` parameter, `configs/policy.yaml: txn_limit_policy ∈ {P1, P2}`, and both settings are run in `results/sensitivity.md`. **Default P2** (backoff 26h `[ASSUMPTION]`, max 1 retry, then `contact_update_instrument`).

The disagreement is worth recording rather than hiding: over-conservatism is not free, and its cost is exactly what this harness measures.

---

## 6. UPI failures (source 3)

| Code | Razorpay's documented description | retry_class | Resolution | basis | Backoff / cap | Action |
|---|---|---|---|---|---|---|
| `insufficient_funds` | Account did not have enough funds | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` | 24h / 3 | `retry_payment` |
| `bank_technical_error` | Downtime on the **UPI provider** | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` | 6h / 3 | `retry_payment` |
| `gateway_technical_error` → *partner bank technical issues* | Technical issues at the partner bank; **docs explicitly recommend attempting again after some time** | `RETRY_TIMED` | `NONE_NEEDED` | **`doc_supported`** | 6h / 3 | `retry_payment` |
| `gateway_technical_error` → *partner bank downtime* | Downtime on the partner bank | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` | 6h / 3 | `retry_payment` |
| `payment_declined` | **Funds could not be debited from the customer's account**; docs suggest another attempt | `RETRY_TIMED` | `NONE_NEEDED` | `doc_supported` | 24h / 2 | `retry_payment` |
| `credit_failed` → *bank account mismatch* | Customer used an account other than the one registered with the business | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_use_registered_account` |
| `credit_failed` → *partner bank downtime* | Downtime on the partner bank | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` | 6h / 3 | `retry_payment` |
| `payment_timed_out` → *partner bank downtime* | Downtime at the partner bank | `RETRY_TIMED` | `NONE_NEEDED` | `project_inference` | 6h / 3 | `retry_payment` |
| `invalid_vpa` | Customer is not a valid user on the UPI app; must complete registration by linking a bank account | `NO_RETRY` | `CUSTOMER_ACTION` | `doc_supported` | — | `contact_complete_upi_registration` |
| `vpa_resolution_failed` | Failed to process using the customer's UPI ID; **docs direct merchants to raise a support ticket** | `NO_RETRY` | `MERCHANT_ESCALATION` | `doc_supported` | — | `escalate_support_ticket` |

**Note the asymmetry with cards.** UPI `gateway_technical_error` retry is `doc_supported`; the card version of the same code name is only `project_inference`. Same code, different page, different evidential weight. One rule must not be applied to both.

**Attended-only, excluded (§2):** `payment_cancelled`, `payment_collect_request_expired`, `payment_timed_out` (customer sub-case).

---

## 7. `payment_risk_check_failed` — deliberate departure from documented guidance

Razorpay documents that the bank declined the payment citing it as fraudulent, and recommends advising the customer to try another card.

**We do not follow that recommendation, and the reasoning is ours, not Razorpay's.** The documented advice assumes a human at a checkout choosing to present a different card. An automated system that responds to a fraud decline by cycling through payment instruments is behaviour we judge unacceptable in an unattended agent, and the buildathon explicitly disqualifies offense-capable tooling. Razorpay does not characterise this pattern; the characterisation and the decision are ours.

Gate behaviour: terminate the episode, emit `reason_code=RISK_DECLINE_STOP`, notify the merchant, take no further automated action. `tests/test_gate_risk_stop.py` asserts zero subsequent actions.

---

## 8. The `card_declined` / `payment_failed` bucket

Razorpay states it may not have access to the underlying decline reason, because issuing banks often do not provide it `[CITE]`. That makes this an **important ambiguous bucket**: a generic decline that was in fact transient becomes a lost retry under our fail-safe.

We make **no claim about how common this is in production** — we have no source for that, and an earlier draft of this file asserted it was likely the highest-volume bucket. That assertion is withdrawn. What we can state is a design fact we control: it is **25% of our modelled population** (`EVAL.md` §3.2), a `[MODEL]` weight, and swept.

Reporting obligation: recovery rate and net ₹ for this bucket are broken out separately in every eval run. If A3's uplift comes mainly from here, state it.

---

## 9. UNVERIFIED — must not be emitted by the simulator

Present in an earlier draft, **not found on sources 2, 3 or 4**. They may exist on source 1, which did not render. Each must be confirmed with a working anchor link on an appropriate payment-error page, or deleted.

`incorrect_otp` · `otp_expired` · `otp_attempts_exceeded` · `incorrect_pin` · `pin_attempts_exceeded` · `card_number_invalid` · `incorrect_card_details` · `incorrect_card_expiry_date` · `incorrect_cardholder_name` · `international_transaction_not_allowed` · `transaction_daily_limit_exceeded` · `transaction_frequency_limit_exceeded` · `upi_app_technical_error` · `authorisation_declined_by_psp` · `psp_app_not_available`

Rules `[INVARIANT]`:
- All resolve to `NO_RETRY` + `escalate_unknown_failure`.
- **None may be emitted by the simulator** (`tests/test_unverified_not_emitted.py`).
- **Do not promote a code because it appears in an unrelated Razorpay integration or API-reference page.** Verification means the code appears on a payment-error page with a documented failure description and next step.

Notes: `transaction_daily_limit_exceeded` may duplicate the card `transaction_limit_exceeded`, which the docs already define as a daily limit — confirm before adding both. Most of the OTP/PIN/card-data codes are attended-only and fall outside the cohort even if verified; do not spend time on them.

---

## 10. BLOCKING — mandate and subscription terminal failures

`EVAL.md` scopes an episode to a failed **subscription/mandate** debit. This file covers only generic card and UPI payment errors. The failures that actually terminate a mandate are absent:

- mandate revoked / cancelled by the customer
- mandate expired
- debit amount above the registered maximum
- pre-debit notification failure
- account closed or frozen (eNACH)

These must be verified against **Razorpay's Subscriptions / eMandate / Recurring Payments documentation**, not the generic card and UPI error pages, and the §3.2 mix in `EVAL.md` reweighted.

**`sim-v1` cannot be tagged until this closes.** These are the codes where a wrong retry is a compliance failure rather than a wasted rupee, and an agent that handles insufficient-funds beautifully while retrying a revoked mandate fails the track's bar.

---

## 11. Retry caps

`EVAL.md` §5.2 lists "attempts exceeding network/issuer retry limits" as a zero-tolerance gate. **No external limit is cited, because we have not sourced one.**

Self-imposed conservative caps `[ASSUMPTION]`: 3 payment attempts per episode for `RETRY_TIMED`, 8 total actions, 30-day window.

Do not cite card network retry rules from memory. Either find the published rule and link it, or state that the caps are self-imposed and conservative. The second is fully defensible; a wrong number is not.
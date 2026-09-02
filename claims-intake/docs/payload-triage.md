# Payload Triage

Every payload in `data/fnol_edge.json` classified against `docs/api-contract.md` as you have completed it. The classification records what the contract says the service does, which is not always what the payload obviously violates.

Fill one row per payload. Where a payload is accepted, leave the rule, code, and status columns as `-`.

## Classification


| Payload | Outcome  | Rule | Code                  | Status |
| ------- | -------- | ---- | --------------------- | ------ |
| EDGE-01 | Accepted | V-2  | CREATED               | 201    |
| EDGE-02 | Accepted | V-4  | CREATED               | 201    |
| EDGE-03 | Accepted | V-3  | CREATED               | 201    |
| EDGE-04 | Rejected | V-7  | POLICY_CANCELLED      | 422    |
| EDGE-05 | Rejected | V-2  | LOSS_BEFORE_INCEPTION | 422    |
| EDGE-06 | Rejected | V-4  | AMOUNT_EXCEEDS_LIMIT  | 422    |
| EDGE-07 | Rejected | V-1  | POLICY_NOT_FOUND      | 422    |
| EDGE-08 | Rejected | N/A  | INVALID_REQUEST       | 400    |
| EDGE-09 | Rejected | V-5  | TYPE_NOT_COVERED      | 422    |
| EDGE-10 | Rejected | V-7  | POLICY_CANCELLED      | 422    |
| EDGE-11 | Rejected | V-5  | INVALID_REQUEST       | 400    |
| EDGE-12 | Accepted | V-4  | CREATED               | 201    |




## Decision log

Three payloads cannot be classified against the contract as it shipped, because the contract left a decision unmade. For each one, record the ambiguity, the decision, its authority, and the alternative you rejected.

A decision recorded here and nowhere else has not been made. Amend `docs/api-contract.md` so that a reader of the contract alone could not arrive at the other reading.

### Decision 1

**Payload.** EDGE-07

**The ambiguity.** What the contract failed to determine, and the two readings that were both available.

The contract fails to determine is whether policy-number matching is case-sensitive. The two readings are we accept the payload if the provided policy-number is accepted regardless of casing, or we decline because it is the system treats uppercase and lowercase letters as different.

**Decision.** What the service does.

Service currently declines because the casing is different in the policy-number. Error POLICY_NOT_FOUND 422 is thrown.

**Authority.** The work item, acceptance criterion, or product rule that supports it.

POLICY_NOT_FOUND/422

**Rejected alternative.** The other reading, and why it is wrong rather than merely less preferred.

We accept the policy-number because regardless of casing it would match policy MOT-4471. This is wrong because policy mot-4471 could be totally different from MOT-4471, so we could encounter an error if we allow it.

**Contract amended.** Section and what changed. 

Added in 4.3, first part.

### Decision 2

**Payload.** EDGE-12

**The ambiguity.** The contract fails to determine what to do when the estimated amount contains 3 decimal places. The two readings are we accept the payload as if the estimated_amount under the policy limit, or we decline because the format of the number is malformed.

**Decision.**

Service currently accepts because the estimated_amount is well under the policy limit of 75000.00.

**Authority.**

V-4

**Rejected alternative.** 

We decline the payload because the number of decimal places is different in the estimated_amount and the limit. This is wrong because we are comparing if the limit is less than, greater than, or equal, the number of decimal places will not affect the outcome of the boolean result, and we can always fill extra decimal places with placeholder zeros.

**Contract amended.**

Added in 4.3, second part.

### Decision 3

**Payload.** EDGE-11

**The ambiguity.** The contract fails to determine what to do when a passed claim field is not one of the values in the contract. The two readings are we accept the payload as the field will be covered by rule V-5, or we reject as flood is not one of the types in 2.3.

**Decision.** Service currently rejects because the field is not one of the valid fields in 2.3. Error INVALID_REQUEST 400 is thrown.

**Authority.** 2.3, 2.4

**Rejected alternative.** We accept the payload as any type provided will be checked via rule V-5. This is wrong because flood is not a valid claim type, and V-5 should only be used for fields declared in 2.3.

**Contract amended.**

Added in 4.3, third part.

## Reconciliation Note

Compared `NotificationRequest` constraints in `src/claims/models.py` to contract section 6. Every refusal outputs a status of 400. Section 6 already had `INVALID_REQUEST` for missing/malformed bodies (section 2.4). No new error code was required.

Outside of 2.4, I also checked a list of constraints that the model should enforce. This includes empty `policy_number` and `claim_type`, `loss_date` that is not a calendar date, `estimated_amount` not greater than zero; `estimated_amount` with other than two decimal places. Those were added under the existing `INVALID_REQUEST` code of status 400.`claim_type` values outside 2.3 are also constrained by the model. They also stay under the existing `INVALID_REQUEST` code of status 400.

Section 4.3 was modified because decimal places of estimated amount must be exactly 2, so EDGE-12 is now INVALID_REQUEST 400 and not accepted under V-4.
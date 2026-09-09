# Claims Intake Service: API Contract

Version 0.4. Owned by the claims intake team. Consumed by the claims portal team.

This document is the authority on what the service accepts, what it returns, and under what conditions it refuses. Where the code and this document disagree, the document is correct and the code is a defect.

Sections 1 through 3 are fixed. Do not edit them.

## 1. Purpose and scope

The claims intake service accepts a first notice of loss from the claims portal, validates it against the policy master and a table of business rules, and either records a notification and issues a claim reference or refuses the submission with a specific reason.

**In scope.** Accepting a notification, validating it, and recording it. Issuing a claim reference. Reporting the reason a notification was refused.

**Out of scope.** Adjusting, reserving, payment, and any decision about coverage beyond the rules in section 4. The service decides whether a notification is well formed and admissible. It does not decide whether the claim will be paid.

**The policy master is a dependency, not part of this service.** The service reads policy records from it and does not write to it. A policy that cannot be read is a condition this contract specifies, and it is specified separately from a policy that does not exist, because the two require different action from the caller.

**Compatibility.** Adding a field to a response is a compatible change and callers must ignore fields they do not recognize. Adding a new error code is a compatible change and callers must fall through to default handling for a code they do not recognize. Changing the meaning of an existing code, removing a field, or changing a status code for an existing condition is not compatible and does not happen without a version increment agreed with the portal team.

## 2. Request



### 2.1 Endpoint

```
POST /notifications
Content-Type: application/json
```



### 2.2 Body


| Field              | Type    | Required | Notes                                                         |
| ------------------ | ------- | -------- | ------------------------------------------------------------- |
| `policy_number`    | string  | yes      | Identifier as held in the policy master. Not empty.           |
| `loss_date`        | date  | yes      | Calendar date, `YYYY-MM-DD`.                                  |
| `claim_type`       | string  | yes      | One of the values in 2.3. Not empty.                          |
| `estimated_amount` | decimal | yes      | United States dollars, two decimal places. Greater than zero. |
| `description`      | string  | no       | Free text. Absent and `null` are equivalent.                  |


The service rejects a body carrying a field not listed above. A misspelled field name is a defect in the caller's code, and accepting the payload with the field ignored would record a notification built from data the caller did not send.

### 2.3 Claim type vocabulary

`collision`, `theft`, `glass`, `liability`, `weather`.

Which of these are admissible on a given notification depends on the product the policy is written on. The vocabulary is fixed by this contract. The permitted subset is a property of the policy record and is evaluated by rule `V-5`.

### 2.4 Well formed against acceptable

A request that cannot be interpreted is refused with status `400`. This means the body was not valid JSON, a required field was abs**e**nt, a field carried a value of the wrong type, or a field was present that this contract does not define. The caller's code is wrong.

A request that was interpreted and whose content is not admissible is refused with status `422`. The caller's data is wrong, and a person needs to see the reason.

This split is stated here once and holds without exception everywhere else in this document.

## 3. Success response

A notification that passes every rule in section 4 is recorded and the service responds:

```
201 Created
Content-Type: application/json

{
  "claim_reference": "CLM-2026-000317",
  "status": "recorded"
}
```

`claim_reference` matches the pattern `CLM-YYYY-NNNNNN`, where `YYYY` is the calendar year in which the notification was recorded and `NNNNNN` is a zero padded sequence. A claim reference is unique across all recorded notifications and is never reissued. It is the value the claims handler quotes and the value every downstream system keys on.

`status` is `recorded` on every success response this contract defines. It exists because the portal displays it and because a future state that is not `recorded` is foreseeable. Callers must not treat it as constant.

A refused notification is never recorded and no claim reference is issued. There is no partial outcome: either a notification exists with a reference, or nothing was written.

## 4. Validation



### 4.1 Evaluation order

Rules are evaluated from top to bottom. Evaluation stops at the first failure and that rule's code is returned. V-1 short circuits: if it fails, no rule that reads a policy field is evaluated. For these, a JSON is returned with the failure containing the rule's code.

### 4.2 Rule table


| ID  | Condition                                                                                             | Code                     | Status |
| --- | ----------------------------------------------------------------------------------------------------- | ------------------------ | ------ |
| V-1 | `policy_number` exists in the policy master                                                           | `POLICY_NOT_FOUND`       | 422    |
| V-6 | (`policy_number`, `loss_date`, `claim_type`) != recorded (`policy_number`, `loss_date`, `claim_type`) | `DUPLICATE_NOTIFICATION` | 409    |
| V-7 | `loss_date` < policy `cancellation_date` OR policy.cancellation_date IS NULL                          | `POLICY_CANCELLED`       | 422    |
| V-2 | `loss_date` >= policy `effective_date`                                                                | `LOSS_BEFORE_INCEPTION`  | 422    |
| V-3 | `loss_date` <= policy `expiry_date`                                                                   | `LOSS_AFTER_EXPIRY`      | 422    |
| V-4 | `estimated_amount` <= policy `limit`                                                                  | `AMOUNT_EXCEEDS_LIMIT`   | 422    |
| V-5 | `claim_type` permitted on the policy's product                                                        | `TYPE_NOT_COVERED`       | 422    |


Boundaries are inclusive as written. A loss on the inception date is
covered (WI-0142, AC-3). An amount equal to the limit is within cover.

### 4.3 Contract Amended

All policy-numbers are case sensitive, thus for example mot-4471 and MOT-4471 are completely different and represent different policies.

The length of a decimal of the estimated_amount must be exactly 2, otherwise an INVALID_REQUEST 400 will occur.

Any claim types that are not included as one of the fields from 2.3 are rejected.

## 5. Error envelope

Every non-2xx response returns this shape and no other.
Example 1:
{
  "code": "POLICY_NOT_FOUND",
  "message": "Policy number does not exist in policy master.",
  "detail": {
    "rule": "V-1",
    "policy_number": "MOT-4444"
  }
}
Example 2:
{
  "code": "POLICY_CANCELLED",
  "message": "Loss date precedes policy cancellation.",
  "detail": {
    "rule": "V-7",
    "loss_date": "2026-02-01",
    "cancellation_date": "2026-01-01"
  }
}
Example 3:
{
  "code": "INVALID_REQUEST",
  "message": "Request is missing required fields or malformed.",
  "detail": {
    "missing_fields": ["loss_date"]
  }
}

`code` is stable and callers branch on it. `message` is for display and
may change without notice. `detail` carries the values that produced
the decision and its keys vary by code.

## 6. Status code mapping

return {
  "code": "POLICY_NOT_FOUND",
  "message": "Policy number does not exist in policy master.",
  "detail": { "rule": "V-1", "policy_number": _ }
}, 422

return {
  "code": "DUPLICATE_NOTIFICATION",
  "message": "Notification already exists in system.",
  "detail": { "rule": "V-6", "policy_number": _, "loss_date": _, "claim_type": _ }
}, 409

return {
  "code": "POLICY_CANCELLED",
  "message": "Loss date precedes policy cancellation.",
  "detail": { "rule": "V-7", "policy_number": _, "loss_date": _, "cancellation_date": _ }
}, 422

return {
  "code": "LOSS_BEFORE_INCEPTION",
  "message": ""Loss date precedes policy inception.,
  "detail": { "rule": "V-2", "policy_number": _, "loss_date": _, "effective_date": _}
}, 422

return {
  "code": "LOSS_AFTER_EXPIRY",
  "message": "Loss date succeeds policy expiration.",
  "detail": { "rule": "V-3", "policy_number": _, "loss_date": _, "expiry_date": _ }
}, 422

return {
  "code": "AMOUNT_EXCEEDS_LIMIT",
  "message": "Estimated amount exceeds policy limit.",
  "detail": { "rule": "V-4", "policy_number": _, "estimated_amount": _, "limit": _ }
}, 422

return {
  "code": "TYPE_NOT_COVERED",
  "message": "Claim type is not permitted for this policy.",
  "detail": { "rule": "V-5", "policy_number": _, "permitted_claim_types": _ }
}, 422

return {
  "code": "LOOKUP_TIMEOUT",
  "message": "Server took too long to lookup. Please try again.",
  "detail": { ... }
}, 504

return {
  "code": "UNREACHABLE_DEPENDENCY",
  "message": "Cannot connect to backend resource. Please try again.",
  "detail": { ... }
}, 503

return {
  "code": "INVALID_DEPENDENCY",
  "message": "Request is missing required fields or malformed. Please try again.",
  "detail": { ... }
}, 502

return {
  "code": "INVALID_REQUEST",
  "message": "Invalid or unparsable response. Please try again.",
  "detail": { ... }
}, 400
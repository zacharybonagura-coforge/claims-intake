# Agent log

Record of two agent-produced changes during the rule-engine assignment: one accepted, one rejected. Reasons cite the contract or a work-item criterion, not preference.

## Accepted: V-6 is not a POLICY_RULES entry

**What the agent produced.** A design for `evaluate_notification`: `POLICY_RULES` holds only `(notification, policy) -> ValidationOutcome` functions (V-7, V-2, V-3, V-4, V-5). V-6 runs in the orchestrator via `repository.find_matching` after V-1 and before those rules, with a comment stating why it is not in the tuple.

**Decision.** Accepted and implemented that way.

**Reason.** Contract section 4.1 fixes evaluation order: V-1, then V-6, then V-7 through V-5, stopping at the first failure. V-6 is a query against recorded notifications (WI-0151 AC-1; `find_matching` in the repository). The other rules compare notification fields to a policy. Putting `find_matching` inside `POLICY_RULES` would make every "policy rule" take a repository, so a duplicate check could not stay a query and the pure rules could not be unit-tested with only a `Policy`. 

## Rejected: AC-3 test that only called evaluate_notification twice

**What the agent produced.**

```python
def test_v6_does_not_treat_an_unrecorded_refusal_as_a_duplicate(...):
    """WI-0151 AC-3. A submission that was never written cannot be duplicated."""
    first = evaluate_notification(motor_notification, policy_client, repository)
    second = evaluate_notification(motor_notification, policy_client, repository)
    assert first.code != "DUPLICATE_NOTIFICATION"
    assert second.code != "DUPLICATE_NOTIFICATION"
```

`motor_notification` is a valid FNOL (`MOT-4471`, loss in term). Neither call is a refusal, and `evaluate_notification` never writes.

**Decision.** Rejected. Replaced with `test_v6_rejected_submission_is_not_a_duplicate_on_retry`, which calls submit_notification twice on a payload that fails V-2 (`loss_date` before inception), asserts `LOSS_BEFORE_INCEPTION`, asserts `find_matching` is still `None`, then asserts the retry is the same refusal, not `DUPLICATE_NOTIFICATION`.

**Reason.** WI-0151 AC-3: "A notification matching a previous submission that was rejected is not a duplicate. Nothing was recorded, so there is nothing to duplicate." The agent’s test never rejected a submission and never went through the function that can `record()`. evaluate_notification cannot create a duplicate by design, so the test would still pass if `submit_notification` recorded failed claims and a retry became `DUPLICATE_NOTIFICATION`. That is the defect AC-3 exists to prevent.
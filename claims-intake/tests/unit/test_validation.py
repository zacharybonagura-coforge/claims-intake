from datetime import date
from decimal import Decimal

import pytest

from claims.models import NotificationRequest
from claims.policy_client import StubPolicyClient
from claims.service import evaluate_policy_exists

test_notification = NotificationRequest(
    policy_number="MOT-4471",
    loss_date=date(2026, 4, 2),
    claim_type="collision",
    estimated_amount=Decimal("4200.00"),
    description="Rear ended at a junction."
)

@pytest.mark.parametrize(
    ("policy_number", "expected"),
    [
        ("MOT-4471", None),
        ("mot-4471", "POLICY_NOT_FOUND"),
        (1234, "POLICY_NOT_FOUND")
    ],
    ids=[
        "policy_does_exist",
        "policy_does_not_exist_str",
        "policy_is_int"
    ],
)
def test_v1_finds_existing_policy(policy_number: str, expected: str | None, 
                                  policy_client: StubPolicyClient) -> None:
    test_notification.policy_number = policy_number

    outcome = evaluate_policy_exists(test_notification, policy_client)

    assert outcome.code == expected

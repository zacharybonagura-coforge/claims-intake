from datetime import date
from decimal import Decimal

import pytest

from claims.models import NotificationRequest, Policy
from claims.policy_client import StubPolicyClient
from claims.service import (
    evaluate_loss_after_inception,
    evaluate_policy_exists,
    evaluate_policy_not_cancelled,
)


@pytest.fixture
def motor_notification() -> NotificationRequest:
    return NotificationRequest(
        policy_number="MOT-4471",
        loss_date=date(2026, 4, 2),
        claim_type="collision",
        estimated_amount=Decimal("4200.00"),
        description="Rear ended at a junction.",
    )

@pytest.fixture
def motor_policy() -> Policy:
    return Policy(
        policy_number="MOT-4471",
        product="personal_auto_standard",
        effective_date=date(2026, 3, 1),
        expiry_date=date(2027, 2, 28),
        cancellation_date=None,
        limit=Decimal("50000.00"),
        permitted_claim_types=("collision", "theft", "glass", "liability", "weather"),
    )

@pytest.mark.parametrize(
    ("policy_number", "expected"),
    [
        ("MOT-4471", None),
        ("mot-4471", "POLICY_NOT_FOUND")
    ],
    ids=[
        "policy_does_exist",
        "policy_does_not_exist_str"
    ],
)
def test_v1_finds_existing_policy(
    motor_notification: NotificationRequest, 
    policy_number: str, 
    expected: str | None,
    policy_client: StubPolicyClient
) -> None:

    notification = motor_notification.model_copy(update={"policy_number": policy_number})
    outcome = evaluate_policy_exists(notification, policy_client)

    assert outcome.code == expected


@pytest.mark.parametrize(
    ("cancellation_date", "loss_date", "expected"),
    [
        (date(2026, 6, 1), date(2026, 5, 31), None),
        (date(2026, 6, 1), date(2026, 6, 1), "POLICY_CANCELLED"),
        (date(2026, 6, 1), date(2026, 6, 2), "POLICY_CANCELLED"),
        (None, date(2026, 6, 1), None),
    ],
    ids=[
        "day_before_cancellation_is_covered",
        "cancellation_date_itself_is_not_covered",
        "after_cancellation_is_not_covered",
        "uncancelled_policy_is_unaffected",
    ],
)
def test_v7_ends_cover_at_the_cancellation_date(
    motor_notification: NotificationRequest,
    motor_policy: Policy,
    cancellation_date: date | None, 
    loss_date: date, 
    expected: str | None
) -> None:
    """WI-0158 AC-1, AC-2, AC-3. Cancellation takes effect at the start
    of the cancellation date, so a loss on that date is not covered."""
    notification = motor_notification.model_copy(update={"loss_date":loss_date})
    policy = motor_policy.model_copy(update={"cancellation_date": cancellation_date})

    outcome = evaluate_policy_not_cancelled(notification, policy)

    assert outcome.code == expected


@pytest.mark.parametrize(
    ("effective_date", "loss_date", "expected"),
    [
        (date(2026, 5, 30), date(2026, 5, 31), None),
        (date(2026, 6, 1), date(2026, 6, 1), None),
        (date(2026, 6, 1), date(2026, 5, 31), "LOSS_BEFORE_INCEPTION"),
    ],
    ids=[
        "day_after_effective_date_covered",
        "day_on_effective_date_covered",
        "day_before_effective_date_not_covered",
    ],
)
def test_v2_covers_on_or_after_effective_date(
    motor_notification: NotificationRequest,
    motor_policy: Policy,
    effective_date: date, 
    loss_date: date, 
    expected: str | None
) -> None:
    """WI-0142 AC-1 and AC-3. Cover takes effect on and after
    the effective date, so a loss on that date is covered. A loss
    before effective date is not covered. AC-4 is covered by V-1."""
    notification = motor_notification.model_copy(update={"loss_date":loss_date})
    policy = motor_policy.model_copy(update={"effective_date": effective_date})

    outcome = evaluate_loss_after_inception(notification, policy)

    assert outcome.code == expected

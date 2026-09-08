from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from claims.models import ClaimType, NotificationRequest, Policy
from claims.policy_client import StubPolicyClient
from claims.repository import NotificationRepository
from claims.service import (
    evaluate_amount_within_limit,
    evaluate_claim_type_covered,
    evaluate_loss_after_inception,
    evaluate_loss_before_expiry,
    evaluate_notification,
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


@pytest.fixture
def repository() -> NotificationRepository:
    return NotificationRepository()


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


@pytest.mark.parametrize(
    ("expiry_date", "loss_date", "expected"),
    [
        (date(2026, 6, 1), date(2026, 5, 31), None),
        (date(2026, 6, 1), date(2026, 6, 1), None),
        (date(2026, 5, 31), date(2026, 6, 1), "LOSS_AFTER_EXPIRY"),
    ],
    ids=[
        "day_before_expiry_date_covered",
        "day_on_expiry_date_covered",
        "day_after_expiry_date_not_covered",
    ],
)
def test_v3_covers_on_or_before_expiry_date(
    motor_notification: NotificationRequest,
    motor_policy: Policy,
    expiry_date: date, 
    loss_date: date, 
    expected: str | None
) -> None:
    """Contract 4.2 V-3. Cover includes the expiry date. A loss after 
    the expiry date is not covered."""
    notification = motor_notification.model_copy(update={"loss_date":loss_date})
    policy = motor_policy.model_copy(update={"expiry_date": expiry_date})

    outcome = evaluate_loss_before_expiry(notification, policy)

    assert outcome.code == expected


@pytest.mark.parametrize(
    ("claim_type", "permitted_claim_types", "expected"),
    [
        ("collision", ("collision", "theft", "glass", "liability", "weather"), None),
        ("collision", ("theft", "glass", "weather", "liability"), "TYPE_NOT_COVERED"),
    ],
    ids=[
        "claim_type_in_permitted_claim_types_covered",
        "claim_type_not_in_permitted_claim_types_not_covered",
    ],
)
def test_v5_covers_valid_types(
    motor_notification: NotificationRequest,
    motor_policy: Policy,
    claim_type: ClaimType, 
    permitted_claim_types: tuple[ClaimType, ...], 
    expected: str | None
) -> None:
    """Contract 4.2 V-5. A claim_type in 2.3 is covered only if it is permitted on the
    policy's product. Unknown types are INVALID_REQUEST and never reach this rule."""
    notification = motor_notification.model_copy(update={"claim_type": claim_type})
    policy = motor_policy.model_copy(update={"permitted_claim_types": permitted_claim_types})

    outcome = evaluate_claim_type_covered(notification, policy)

    assert outcome.code == expected


@pytest.mark.parametrize(
    ("estimated_amount", "limit", "expected"),
    [
        (Decimal("49999.99"), Decimal("50000.00"), None),
        (Decimal("50000.00"),  Decimal("50000.00"), None),
        (Decimal("50000.01"),  Decimal("50000.00"), "AMOUNT_EXCEEDS_LIMIT"),
    ],
    ids=[
        "estimated_amount_below_limit_covered",
        "estimated_amount_at_limit_covered",
        "estimated_amount_above_limit_not_covered",
    ],
)
def test_v4_covers_amount_not_exceeding_limit(
    motor_notification: NotificationRequest,
    motor_policy: Policy,
    estimated_amount: Decimal, 
    limit: Decimal, 
    expected: str | None
) -> None:
    """Contract 4.2 V-4. Cover includes estimated_amount at limit. A loss with 
    estimated_amount greater than limit is not covered."""
    notification = motor_notification.model_copy(update={"estimated_amount": estimated_amount})
    policy = motor_policy.model_copy(update={"limit": limit})

    outcome = evaluate_amount_within_limit(notification, policy)

    assert outcome.code == expected


def test_v6_rejects_a_recorded_duplicate(
    motor_notification: NotificationRequest,
    policy_client: StubPolicyClient,
    repository: NotificationRepository,
) -> None:
    """WI-0151 AC-1. Same policy_number, loss_date, and claim_type
    as a recorded notification is DUPLICATE_NOTIFICATION. Detail carries
    the existing claim reference."""
    recorded = repository.record(motor_notification)
    outcome = evaluate_notification(motor_notification, policy_client, repository)
    assert outcome.code == "DUPLICATE_NOTIFICATION"
    assert outcome.detail["claim_reference"] == recorded.claim_reference


@pytest.mark.parametrize(
    "update",
    [
        {"policy_number": "MOT-4472"},
        {"loss_date": date(2026, 4, 3)},
        {"claim_type": "theft"},
    ],
    ids=[
        "policy_number_differs",
        "loss_date_differs",
        "claim_type_differs",
    ],
)
def test_v6_allows_when_only_two_fields_match(
    motor_notification: NotificationRequest,
    policy_client: StubPolicyClient,
    repository: NotificationRepository,
    update: dict[str, Any],
) -> None:
    """Only two matching policy_number, loss_date, and claim_type
    as a recorded notification is valid."""
    repository.record(motor_notification)
    notification = motor_notification.model_copy(update=update)
    outcome = evaluate_notification(notification, policy_client, repository)
    assert outcome.code != "DUPLICATE_NOTIFICATION"

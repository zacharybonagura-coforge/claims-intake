"""HTTP integration tests for POST /notifications.

These drive the service through the app. They assert the contract mapping:
status, code, and the detail values that make a refusal actionable.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from claims.api import routes
from claims.policy_client import LookupFailureReason, StubPolicyClient
from claims.repository import NotificationRepository

NOTIFICATION: dict[str, Any] = {
    "policy_number": "MOT-4471",
    "loss_date": "2026-04-02",
    "claim_type": "collision",
    "estimated_amount": "4200.00",
    "description": "Rear ended at a junction.",
}

@pytest.fixture
def client() -> TestClient:
    routes.policy_client = StubPolicyClient()
    routes.repository = NotificationRepository()
    return TestClient(routes.app)


def test_accepted_notification_returns_201_with_claim_reference(client: TestClient) -> None:
    response = client.post("/notifications", json=NOTIFICATION)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "recorded"
    assert body["claim_reference"].startswith("CLM-")


@pytest.mark.parametrize(
    ("update", "status", "code", "detail"),
    [
        (
            {"policy_number": "MOT-9999"},
            422,
            "POLICY_NOT_FOUND",
            {"rule": "V-1", "policy_number": "MOT-9999"},
        ),
        (
            {"policy_number": "MOT-4496", "loss_date": "2026-03-05", "claim_type": "glass"},
            422,
            "POLICY_CANCELLED",
            {
                "rule": "V-7",
                "policy_number": "MOT-4496",
                "loss_date": "2026-03-05",
                "cancellation_date": "2026-02-01",
            },
        ),
        (
            {"policy_number": "MOT-4479", "loss_date": "2026-02-20"},
            422,
            "LOSS_BEFORE_INCEPTION",
            {
                "rule": "V-2",
                "policy_number": "MOT-4479",
                "loss_date": "2026-02-20",
                "effective_date": "2026-03-15",
            },
        ),
        (
            {"policy_number": "MOT-4489", "loss_date": "2026-03-20", "claim_type": "theft"},
            422,
            "LOSS_AFTER_EXPIRY",
            {
                "rule": "V-3",
                "policy_number": "MOT-4489",
                "loss_date": "2026-03-20",
                "expiry_date": "2026-02-28",
            },
        ),
        (
            {"policy_number": "MOT-4502", "estimated_amount": "14500.00"},
            422,
            "AMOUNT_EXCEEDS_LIMIT",
            {"rule": "V-4", "policy_number": "MOT-4502"},
        ),
        (
            {"policy_number": "MOT-4486", "claim_type": "collision"},
            422,
            "TYPE_NOT_COVERED",
            {"rule": "V-5", "policy_number": "MOT-4486"},
        ),
    ],
    ids=[
        "v1_policy_not_found",
        "v7_policy_cancelled",
        "v2_loss_before_inception",
        "v3_loss_after_expiry",
        "v4_amount_exceeds_limit",
        "v5_type_not_covered",
    ],
)
def test_rule_rejection(
    client: TestClient,
    update: dict[str, Any],
    status: int,
    code: str,
    detail: dict[str, Any],
) -> None:
    response = client.post("/notifications", json={**NOTIFICATION, **update})

    assert response.status_code == status
    body = response.json()
    assert body["code"] == code
    for key, value in detail.items():
        assert key in body["detail"]
        assert body["detail"][key] == value


def test_duplicate_notification_returns_409(client: TestClient) -> None:
    first = client.post("/notifications", json=NOTIFICATION)
    second = client.post("/notifications", json=NOTIFICATION)

    assert first.status_code == 201
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "DUPLICATE_NOTIFICATION"
    assert body["detail"]["rule"] == "V-6"
    assert body["detail"]["policy_number"] == NOTIFICATION["policy_number"]
    assert body["detail"]["loss_date"] == NOTIFICATION["loss_date"]
    assert body["detail"]["claim_type"] == NOTIFICATION["claim_type"]
    assert body["detail"]["claim_reference"] == first.json()["claim_reference"]


def test_parse_failure_returns_400(client: TestClient) -> None:
    body = {k: v for k, v in NOTIFICATION.items() if k != "loss_date"}
    response = client.post("/notifications", json=body)

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "INVALID_REQUEST"
    assert "loss_date" in payload["detail"]["missing_fields"]


@pytest.mark.parametrize(
    ("reason", "status", "code"),
    [
        ("timeout", 504, "LOOKUP_TIMEOUT"),
        ("unreachable", 503, "UNREACHABLE_DEPENDENCY"),
        ("unparsable", 502, "INVALID_DEPENDENCY"),
    ],
    ids=["timeout", "unreachable", "unparsable"],
)
def test_policy_lookup_failure(
    client: TestClient,
    reason: LookupFailureReason,
    status: int,
    code: str,
) -> None:
    routes.policy_client.fail_with = reason
    response = client.post("/notifications", json=NOTIFICATION)

    assert response.status_code == status
    body = response.json()
    assert body["code"] == code
    assert body["detail"]["policy_number"] == NOTIFICATION["policy_number"]

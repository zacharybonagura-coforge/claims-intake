"""HTTP surface for the claims intake service.

This layer does three things and no more: it parses the request, it calls the
service, and it maps the outcome to a status code. It holds no rule logic. A rule
that appears here is a rule the service layer cannot be tested for.

Day 4 lab. Implement against `docs/api-contract.md` sections 5 and 6.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from claims.models import NotificationRequest, RecordedNotification
from claims.policy_client import PolicyLookupFailed, StubPolicyClient
from claims.repository import NotificationRepository
from claims.service import submit_notification

app = FastAPI(title="Claims Intake Service")

policy_client = StubPolicyClient()
repository = NotificationRepository()

STATUS_BY_CODE = {
    "POLICY_NOT_FOUND": (422, "Policy number does not exist in policy master."),
    "DUPLICATE_NOTIFICATION": (409, "Notification already exists in system."),
    "POLICY_CANCELLED": (422, "Loss date precedes policy cancellation."),
    "LOSS_BEFORE_INCEPTION": (422, "Loss date precedes policy inception."),
    "LOSS_AFTER_EXPIRY": (422, "Loss date succeeds policy expiration."),
    "AMOUNT_EXCEEDS_LIMIT": (422, "Estimated amount exceeds policy limit."),
    "TYPE_NOT_COVERED": (422, "Claim type is not permitted for this policy."),
    "INVALID_REQUEST": (400, "Invalid or unparsable response. Please try again."),
}
LOOKUP_BY_REASON = {
    "timeout": (504, "LOOKUP_TIMEOUT", "Server took too long to lookup. Please try again."),
    "unreachable": (503, "UNREACHABLE_DEPENDENCY", "Cannot connect to backend resource. Please try again."),
    "unparsable": (502, "INVALID_DEPENDENCY", "Request is missing required fields or malformed. Please try again."),
}


def error_response(status: int, code: str, message: str, detail: dict[str, Any]) -> JSONResponse:
    """Build the error envelope from contract section 5.
    Every non-2xx response is this shape and no other. jsonable_encoder is
    required because detail can carry date and Decimal values from a
    ValidationOutcome, which JSON cannot serialize on its own.
    """

    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "detail": jsonable_encoder(detail)},
    )


def missing_field_names(exc: RequestValidationError) -> list[str]:
    """Return the field names FastAPI reported as missing.
    Each error's loc is a path such as ("body", "loss_date"). The last
    element is the field name the contract's example envelope uses.
    """
    return [
        str(err["loc"][-1])
        for err in exc.errors()
        if err["type"] == "missing"
    ]


@app.exception_handler(RequestValidationError)
def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Map a body FastAPI could not parse to 400 INVALID_REQUEST.
    FastAPI validates before create_notification runs, so a malformed body
    never reaches the service. Contract section 2.4 makes that a 400, not
    FastAPI's default 422. detail follows section 5 example 3 when fields
    are missing, and carries the parser errors otherwise.
    """
    status, message = STATUS_BY_CODE["INVALID_REQUEST"]
    missing = missing_field_names(exc)
    detail = {"missing_fields": missing} if missing else {"errors": exc.errors()}
    return error_response(status, "INVALID_REQUEST", message, detail)


@app.post("/notifications")
def create_notification(notification: NotificationRequest) -> JSONResponse:
    """Accept a first notice of loss and return the recorded claim or a refusal.
    FastAPI has already parsed the body into NotificationRequest. This
    function calls submit_notification and maps the result to HTTP:
    201 for a RecordedNotification, the section 6 status for a
    ValidationOutcome, and 504 / 503 / 502 for PolicyLookupFailed.
    It does not evaluate rules.
    """
    try:
        result = submit_notification(notification, policy_client, repository)
    except PolicyLookupFailed as exc:
        reason = exc.reason
        status, code, message = LOOKUP_BY_REASON[reason]
        return error_response(status, code, message, {"policy_number": exc.policy_number})
    
    if isinstance(result, RecordedNotification):
        return JSONResponse(status_code=201, content=result.model_dump())
    if isinstance(result.code, str):
        status, message = STATUS_BY_CODE[result.code]
        return error_response(
            status,
            result.code,
            message,
            {"rule": result.rule, **result.detail},
        )
    raise ValueError("refused notification has no error code")

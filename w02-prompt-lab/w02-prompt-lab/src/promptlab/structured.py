from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from promptlab.adapters.base import CompletionRequest, ModelAdapter


def complete_structured[T: BaseModel](
    adapter: ModelAdapter,
    request: CompletionRequest,
    schema: type[T],
    run_id: str,
    max_repairs: int = 1,
) -> tuple[T, int]:
    """Return a schema-validated completion with a bounded semantic repair loop.

    Transport retry remains inside the adapter.
    Schema/content repair belongs here.

    On validation failure, send the validation error text back to the model and
    instruct it to correct only what the error concerns. Do not perform more
    than max_repairs semantic repair attempts.
    """

    result = adapter.complete(request, run_id)
    parsed, error = _parse_and_validate(result.text, schema)
    if parsed is not None:
        return parsed, 0

    last_error = error
    for tries in range(1, max_repairs + 1):
        new_user_content = _repair_user_content(request, result.text, last_error)
        repair_request = request.model_copy(update={"user_content": new_user_content})
        result = adapter.complete(repair_request, run_id)
        parsed, error = _parse_and_validate(result.text, schema)
        if parsed is not None:
            return parsed, tries
        last_error = error

    raise ValueError(f"schema validation failed after {max_repairs} repair(s): {last_error}")


def _parse_and_validate[T: BaseModel](text: str | None, schema: type[T]) -> tuple[T | None, str]:
    if text is None or not text.strip():
        return None, "empty model response"
    try:
        extracted_json = _extract_json(text)
        return schema.model_validate_json(extracted_json), ""
    except (ValidationError, json.JSONDecodeError) as e:
        return None, str(e)


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return text.strip()
    return text[start : end + 1]


def _repair_user_content(
    request: CompletionRequest,
    previous_text: str | None,
    error: str,
) -> str:
    return (
        "The previous response failed schema validation.\n"
        "Correct only what the validation error concerns. "
        "Do not change fields that are already valid. "
        "Return JSON only.\n\n"
        f"Validation error:\n{error}\n\n"
        f"Previous response:\n{previous_text or ''}\n\n"
        f"Original request:\n{request.user_content}"
    )

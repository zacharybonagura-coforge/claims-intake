"""Day 1 usage-recording contract.

Implement this module by following assignments/W02_Day1_Assignment_LOCAL.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from promptlab.config import Settings
from promptlab.errors import UnknownModelError

class CallRecord(BaseModel):
    """One model-call attempt.

    Add the exact fields and types specified by the Day 1 assignment.
    """
    model_config = ConfigDict(extra="forbid")

    record_id: str
    run_id: str
    timestamp: datetime
    provider: Literal["ollama"]
    model_id: str
    task: Literal["triage", "summarization", "extraction"]
    case_id: str
    prompt_id: str
    prompt_version: str
    attempt: int
    temperature: float
    max_output_tokens: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    latency_ms: int
    cost_usd: float
    stop_reason: str
    error_type: str
    response_text: str


def compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Return the configured provider charge for one model call."""
    for model in Settings.from_env().models.values():
        if model.model_id == model_id:
            return float(model.cost(input_tokens, output_tokens))
    raise UnknownModelError(model_id)


def append_record(record: CallRecord, run_id: str) -> None:
    """Append one JSON record to runs/{run_id}.jsonl without rewriting the file."""
    raise NotImplementedError

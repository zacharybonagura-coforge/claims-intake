from __future__ import annotations

import inspect
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from promptlab.adapters.base import CompletionResult
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import Settings
from promptlab.day1 import load_cases
from promptlab.day2 import CASE_IDS, CASES_PATH, main
from promptlab.usage import CallRecord
import promptlab.day2 as day2


def _record(run_id: str, request, model_id: str) -> CallRecord:
    return CallRecord(
        record_id="00000000-0000-4000-8000-000000000001",
        run_id=run_id,
        timestamp=datetime.now(UTC),
        provider="ollama",
        model_id=model_id,
        task=request.task,
        case_id=request.case_id,
        prompt_id=request.prompt_id,
        prompt_version=request.prompt_version,
        attempt=1,
        temperature=request.temperature,
        max_output_tokens=request.max_output_tokens,
        input_tokens=1,
        output_tokens=1,
        cached_input_tokens=None,
        latency_ms=1,
        cost_usd=0.0,
        stop_reason="stop",
        error_type=None,
        response_text="ok",
    )


def test_day2_covers_all_twelve_summarization_cases() -> None:
    assert list(CASE_IDS) == [
        "S01", "S02", "S03", "S04", "S05", "S06",
        "S07", "S08", "S09", "S10", "S11", "S12",
    ]
    cases = load_cases(CASES_PATH, CASE_IDS)
    assert [case["id"] for case in cases] == list(CASE_IDS)
    assert all(case["task"] == "summarization" for case in cases)
    assert CASES_PATH.name == "summarization.jsonl"


def test_day2_source_has_no_model_identifier_literals() -> None:
    source = inspect.getsource(day2)
    assert "mistral:7b" not in source
    assert "qwen3:8b" not in source


def test_main_runs_both_models_with_identical_request_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env()
    mistral_id = settings.models["mistral"].model_id
    qwen_id = settings.models["qwen"].model_id
    captured: list[tuple[str, object]] = []

    def fake_complete(self: OllamaAdapter, request, run_id: str) -> CompletionResult:
        captured.append((self.model_id, request))
        return CompletionResult(
            succeeded=True,
            text="ok",
            error_type=None,
            records=[_record(run_id, request, self.model_id)],
        )

    monkeypatch.setattr(OllamaAdapter, "complete", fake_complete)
    main()

    assert len(captured) == 24
    model_ids = {model_id for model_id, _ in captured}
    assert model_ids == {mistral_id, qwen_id}

    by_case: dict[str, list[object]] = defaultdict(list)
    for _, request in captured:
        by_case[request.case_id].append(request)
        assert request.task == "summarization"
        assert request.prompt_id == "baseline"
        assert request.prompt_version == "v0"
        assert request.temperature == settings.temperature
        assert request.max_output_tokens == 512

    assert set(by_case) == set(CASE_IDS)
    for requests in by_case.values():
        assert len(requests) == 2
        first, second = requests
        assert first.task == second.task
        assert first.case_id == second.case_id
        assert first.prompt_id == second.prompt_id
        assert first.prompt_version == second.prompt_version
        assert first.temperature == second.temperature
        assert first.max_output_tokens == second.max_output_tokens
        assert first.system == second.system
        assert first.user_content == second.user_content

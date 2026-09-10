from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from promptlab.config import Settings
from promptlab.day1 import CASE_IDS, CASES_PATH, load_cases, render_prompt, truncate_example


@pytest.mark.parametrize(
    ("case_id", "overview"),
    [
        ("E12", "Training Agenda"),
        ("E07", "Seasonal Business Review Policy"),
        ("E11", "Family-Owned Company Review Policy"),
    ],
)
def test_load_cases_returns_requested_extraction_case(case_id: str, overview: str) -> None:
    cases = load_cases(CASES_PATH, (case_id,))
    assert len(cases) == 1
    assert cases[0]["id"] == case_id
    assert cases[0]["task"] == "extraction"
    assert overview in cases[0]["source"]


def test_load_cases_keeps_day1_order() -> None:
    assert [case["id"] for case in load_cases(CASES_PATH, CASE_IDS)] == list(CASE_IDS)


@pytest.mark.parametrize("missing_id", ["E99", "MISSING"])
def test_load_cases_raises_when_id_absent(missing_id: str) -> None:
    with pytest.raises(KeyError, match=missing_id):
        load_cases(CASES_PATH, (missing_id,))


@pytest.mark.parametrize(
    "document_text",
    [
        "short document",
        "1. Document Control\nPolicy name: Example.",
    ],
)
def test_render_prompt_replaces_placeholder(document_text: str) -> None:
    rendered = render_prompt("before\n{document_text}\nafter", document_text)
    assert "{document_text}" not in rendered
    assert document_text in rendered


@pytest.mark.parametrize(
    ("done_reason", "expected_error"),
    [
        ("length", "TruncatedResponseError"),
        ("stop", None),
    ],
)
def test_truncate_example_maps_done_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    done_reason: str,
    expected_error: str | None,
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env()
    cases = [{"id": "E11", "task": "extraction", "source": "policy text"}]

    def fake_generate(
        _settings: Settings,
        _prompt: str,
        *,
        temperature: float,
        num_predict: int,
    ) -> tuple[dict[str, Any], int]:
        assert temperature == settings.temperature
        assert num_predict == 8
        return (
            {
                "prompt_eval_count": 10,
                "eval_count": 8,
                "done_reason": done_reason,
                "response": "truncated",
            },
            12,
        )

    monkeypatch.setattr("promptlab.day1.generate", fake_generate)
    truncate_example(cases, "run-1", "{document_text}", settings, settings.models["mistral"])

    record = json.loads((tmp_path / "runs" / "run-1-truncation.jsonl").read_text().splitlines()[0])
    assert record["case_id"] == "E11"
    assert record["attempt"] == 2
    assert record["max_output_tokens"] == 8
    assert record["stop_reason"] == done_reason
    assert record["error_type"] == expected_error
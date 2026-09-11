from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, ModelConfig, Settings

CASE_IDS = ("E12", "E07", "E11")
CASES_PATH = PROJECT_ROOT / "cases" / "extraction.jsonl"
PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"


def load_cases(path: Path, case_ids: tuple[str, ...]) -> list[dict[str, str]]:
    wanted = set(case_ids)
    found: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row: dict[str, Any] = json.loads(line)
        case_id = str(row["id"])
        if case_id in wanted:
            found[case_id] = {
                "id": case_id,
                "task": str(row["task"]),
                "source": str(row["source"]),
            }
    missing = [case_id for case_id in case_ids if case_id not in found]
    if missing:
        raise KeyError(f"Missing extraction cases: {', '.join(missing)}")
    return [found[case_id] for case_id in case_ids]


def render_prompt(template: str, document_text: str) -> str:
    return template.replace("{document_text}", document_text)


def _system_prompt(template: str) -> str:
    system, _, _ = template.partition("<document>")
    return system.strip()


def truncate_example(
    cases: list[dict[str, str]],
    run_id: str,
    template: str,
    settings: Settings,
    model: ModelConfig,
) -> None:
    e11 = None
    for case in cases:
        if case["id"] == "E11":
            e11 = case
            break
    if e11 is None:
        raise KeyError("Missing extraction case: E11")

    adapter = OllamaAdapter(model_id=model.model_id)
    truncation_run_id = f"{run_id}-truncation"
    result = adapter.complete(
        CompletionRequest(
            task="extraction",
            case_id="E11",
            prompt_id="baseline",
            prompt_version="v0",
            system=_system_prompt(template),
            user_content=e11["source"],
            temperature=settings.temperature,
            max_output_tokens=8,
        ),
        truncation_run_id,
    )
    record = result.records[-1]
    print("E11 truncation", record.stop_reason, record.error_type, record.output_tokens)


def main() -> None:
    settings = Settings.from_env()
    adapter = OllamaAdapter(model_id=settings.models["mistral"].model_id)
    run_id = str(uuid.uuid4())
    template = PROMPT_PATH.read_text(encoding="utf-8")
    cases = load_cases(CASES_PATH, CASE_IDS)

    for case in cases:
        result = adapter.complete(
            CompletionRequest(
                task="extraction",
                case_id=case["id"],
                prompt_id="baseline",
                prompt_version="v0",
                system=_system_prompt(template),
                user_content=case["source"],
                temperature=settings.temperature,
                max_output_tokens=256,
            ),
            run_id,
        )
        record = result.records[-1]
        print(case["id"], record.latency_ms, record.input_tokens, record.output_tokens)

    truncate_example(cases, run_id, template, settings, settings.models["mistral"])


if __name__ == "__main__":
    main()

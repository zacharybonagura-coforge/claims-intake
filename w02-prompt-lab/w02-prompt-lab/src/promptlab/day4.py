from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.day1 import load_cases
from promptlab.prompts import load, render_user
from promptlab.records import OutputRecord, append_record
from promptlab.schemas import TriageOutput, TriageOutputWithAnalysis
from promptlab.scoring import load_gold, score_output
from promptlab.structured import complete_structured

TRIAGE_CASES = PROJECT_ROOT / "cases" / "triage.jsonl"
RUN_PATH = PROJECT_ROOT / "docs" / "day4-run.jsonl"
SCORE_PATH = PROJECT_ROOT / "docs" / "day4-scores.jsonl"
MAX_OUTPUT_TOKENS = 256
CASE_IDS = (
    "T01",
    "T02",
    "T03",
    "T04",
    "T05",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T11",
    "T12",
)
VERSIONS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("v1", TriageOutput),
    ("v2", TriageOutputWithAnalysis),
)


def run_version(
    adapter: OllamaAdapter,
    run_id: str,
    settings: Settings,
    model_name: str,
    prompt_version: str,
    schema: type[BaseModel],
    gold: dict[str, dict[str, Any]],
    run_path: Path,
    score_path: Path,
) -> None:
    template = load("triage", prompt_version)
    cases = load_cases(TRIAGE_CASES, CASE_IDS)
    for case in cases:
        request = CompletionRequest(
            task="triage",
            case_id=case["id"],
            prompt_id="triage",
            prompt_version=prompt_version,
            system=template.system,
            user_content=render_user(template, variables={}, untrusted=case["source"]),
            temperature=settings.temperature,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        try:
            parsed, tries = complete_structured(
                adapter,
                request,
                schema,
                run_id,
                max_repairs=settings.max_schema_repairs,
            )
            output = parsed.model_dump()
            error = None
        except ValueError as exc:
            output = None
            error = str(exc)
            tries = settings.max_schema_repairs

        record = OutputRecord(
            run_id=run_id,
            task="triage",
            case_id=case["id"],
            model_name=model_name,
            model_id=adapter.model_id,
            prompt_version=prompt_version,
            succeeded=output is not None,
            repairs=tries,
            output=output,
            error=error,
        )
        append_record(run_path, record)
        for score in score_output(record, gold[case["id"]]):
            append_record(score_path, score)
        print(prompt_version, case["id"], record.succeeded, record.repairs, record.error or "")


def main() -> None:
    settings = Settings.from_env()
    model = settings.models["mistral"]
    run_id = str(uuid.uuid4())
    adapter = OllamaAdapter(model_id=model.model_id)
    gold = load_gold()
    print("run_id", run_id, "model", model.model_id, "temperature", settings.temperature)

    for prompt_version, schema in VERSIONS:
        run_version(
            adapter=adapter,
            run_id=run_id,
            settings=settings,
            model_name=model.logical_name,
            prompt_version=prompt_version,
            schema=schema,
            gold=gold,
            run_path=RUN_PATH,
            score_path=SCORE_PATH,
        )


if __name__ == "__main__":
    main()
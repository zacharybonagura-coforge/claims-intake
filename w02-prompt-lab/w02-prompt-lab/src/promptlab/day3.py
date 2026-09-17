from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.day1 import load_cases
from promptlab.records import OutputRecord, append_record
from promptlab.schemas import PolicyExtraction, SummarizationOutput, TaskName, schema_description
from promptlab.structured import complete_structured

SUMMARIZATION_CASES = PROJECT_ROOT / "cases" / "summarization.jsonl"
EXTRACTION_CASES = PROJECT_ROOT / "cases" / "extraction.jsonl"
SUMMARIZE_PROMPT = PROJECT_ROOT / "src" / "prompts" / "summarize.v1.md"
EXTRACT_PROMPT = PROJECT_ROOT / "src" / "prompts" / "extract.v2.md"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "day3-run.jsonl"

SUMMARIZATION_IDS = (
    "S01",
    "S02",
    "S03",
    "S04",
    "S05",
    "S06",
    "S07",
    "S08",
    "S09",
    "S10",
    "S11",
    "S12",
)
EXTRACTION_IDS = (
    "E01",
    "E02",
    "E03",
    "E04",
    "E05",
    "E06",
    "E07",
    "E08",
    "E09",
    "E10",
    "E11",
    "E12",
)

def render_prompt(template: str, document_text: str, schema: type[BaseModel]) -> str:
    description = schema_description(schema)
    rendered = template.replace("{schema_description}", description).replace(
        "{document_text}", document_text
    )
    if "{schema_description}" not in template:
        rendered += (
            "\n\nReturn only a JSON object that matches this schema. "
            "Extra keys are forbidden.\n\n"
            f"{description}\n"
        )
    return rendered


def run_task(
    adapter: OllamaAdapter,
    run_id: str,
    settings: Settings,
    model_name: str,
    task: TaskName,
    prompt_id: str,
    prompt_version: str,
    template: str,
    cases_path: Path,
    case_ids: tuple[str, ...],
    schema: type[BaseModel],
    output_path: Path,
) -> None:
    cases = load_cases(cases_path, case_ids)
    for case in cases:
        request = CompletionRequest(
            task=task,
            case_id=case["id"],
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            system="",
            user_content=render_prompt(template, case["source"], schema),
            temperature=settings.temperature,
            max_output_tokens=512,
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
            task=task,
            case_id=case["id"],
            model_name=model_name,
            model_id=adapter.model_id,
            prompt_version=prompt_version,
            succeeded=True,
            repairs=tries,
            output=output,
            error=error,
        )
        append_record(output_path, record)
        print(case["id"], record.succeeded, record.repairs, record.error or "")


def main() -> None:
    settings = Settings.from_env()
    model = settings.models["mistral"]
    run_id = str(uuid.uuid4())
    adapter = OllamaAdapter(model_id=model.model_id)
    output_path = OUTPUT_PATH
    print("run_id", run_id)

    run_task(
        adapter=adapter,
        run_id=run_id,
        settings=settings,
        model_name=model.logical_name,
        task="summarization",
        prompt_id="summarize",
        prompt_version="v1",
        template=SUMMARIZE_PROMPT.read_text(encoding="utf-8"),
        cases_path=SUMMARIZATION_CASES,
        case_ids=SUMMARIZATION_IDS,
        schema=SummarizationOutput,
        output_path=output_path,
    )
    run_task(
        adapter=adapter,
        run_id=run_id,
        settings=settings,
        model_name=model.logical_name,
        task="extraction",
        prompt_id="extract",
        prompt_version="v2",
        template=EXTRACT_PROMPT.read_text(encoding="utf-8"),
        cases_path=EXTRACTION_CASES,
        case_ids=EXTRACTION_IDS,
        schema=PolicyExtraction,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()

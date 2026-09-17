from __future__ import annotations

import argparse
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import cast

from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.corpus import GoldLabel, load_cases, validate_corpus
from promptlab.prompts import load, render_user
from promptlab.records import OutputRecord, ScoreRecord, append_record
from promptlab.report import write_reports
from promptlab.rules import VersionCandidate, select_current_version
from promptlab.schemas import (
    PolicyExtraction,
    StrictModel,
    SummarizationOutput,
    TaskName,
    TriageOutput,
    schema_description,
)
from promptlab.scoring import SCORER_VERSION, score_output
from promptlab.structured import complete_structured

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
TASK_PROMPTS: dict[TaskName, dict[str, tuple[str, str, type[StrictModel]]]] = {
    "triage": {
        "mistral": ("triage", "v3", TriageOutput),
        "qwen": ("triage", "v1", TriageOutput),
    },
    "summarization": {
        "mistral": ("summarize", "v2", SummarizationOutput),
        "qwen": ("summarize", "v2", SummarizationOutput),
    },
    "extraction": {
        "mistral": ("extract", "v2", PolicyExtraction),
        "qwen": ("extract", "v2", PolicyExtraction),
    },
}
MAX_OUTPUT_TOKENS = 512

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local two-model prompt comparison")
    parser.add_argument("--run-id", help="Stable identifier for this run")
    parser.add_argument("--task", choices=["triage", "summarization", "extraction"])
    parser.add_argument("--model", choices=["mistral", "qwen"])
    parser.add_argument("--limit", type=int, help="Limit cases per task for a smoke run")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configuration and corpus without calling Ollama",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Enable model thinking (off by default)"
    )
    return parser


def _version_fields(output: StrictModel) -> tuple[str, str] | None:
    if isinstance(output, SummarizationOutput | PolicyExtraction):
        version = output.version
        effective = output.effective_date
        if (
            version.status == "present"
            and effective.status == "present"
            and isinstance(version.value, str)
            and isinstance(effective.value, str)
        ):
            return version.value, effective.value
    return None


def _add_version_scores(
    *,
    run_id: str,
    task: TaskName,
    model_name: str,
    model_id: str,
    labels: list[GoldLabel],
    outputs: dict[str, StrictModel],
    scores_path: Path,
    all_scores: list[ScoreRecord],
) -> None:
    grouped: dict[str, list[GoldLabel]] = defaultdict(list)
    for label in labels:
        if label.version_group:
            grouped[label.version_group].append(label)

    for group_name, group_labels in grouped.items():
        if len(group_labels) < 2:
            continue
        expected = next(
            (
                label.expected_current_case_id
                for label in group_labels
                if label.expected_current_case_id
            ),
            None,
        )
        as_of_raw = next((label.as_of for label in group_labels if label.as_of), None)
        if expected is None or as_of_raw is None:
            continue
        candidates: list[VersionCandidate] = []
        for label in group_labels:
            output = outputs.get(label.id)
            if output is None:
                continue
            extracted = _version_fields(output)
            if extracted is None:
                continue
            version, effective_raw = extracted
            try:
                effective = date.fromisoformat(effective_raw)
            except ValueError:
                continue
            candidates.append(
                VersionCandidate(case_id=label.id, version=version, effective_date=effective)
            )

        selected = select_current_version(candidates, date.fromisoformat(as_of_raw))
        prompt_id, prompt_version, _schema = TASK_PROMPTS[task][model_name]
        record = ScoreRecord(
            run_id=run_id,
            task=task,
            case_id=f"version:{group_name}",
            model_name=model_name,
            model_id=model_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            scorer_version=SCORER_VERSION,
            metric="version_selection_accuracy",
            numerator=int(selected is not None and selected.case_id == expected),
            denominator=1,
            detail=f"expected={expected}; selected={selected.case_id if selected else 'none'}",
        )
        append_record(scores_path, record)
        all_scores.append(record)


def main() -> None:
    args = _parser().parse_args()
    counts = validate_corpus()
    if args.validate_only:
        print("Corpus valid: " + ", ".join(f"{task}={count}" for task, count in counts.items()))
        return

    run_id = cast(str | None, args.run_id)
    if run_id is None or not RUN_ID_PATTERN.fullmatch(run_id):
        raise SystemExit("--run-id is required and must use letters, numbers, '.', '_' or '-'")
    limit = cast(int | None, args.limit)
    if limit is not None and limit < 1:
        raise SystemExit("--limit must be at least 1")

    selected_tasks: list[TaskName]
    if args.task:
        selected_tasks = [cast(TaskName, args.task)]
    else:
        selected_tasks = ["triage", "summarization", "extraction"]

    settings = Settings.from_env()
    selected_models = [cast(str, args.model)] if args.model else list(settings.models)
    run_dir = PROJECT_ROOT / "runs" / run_id
    if run_dir.exists():
        raise SystemExit(f"Run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    outputs_path = run_dir / "outputs.jsonl"
    scores_path = run_dir / "scores.jsonl"

    all_outputs: list[OutputRecord] = []
    all_scores: list[ScoreRecord] = []
    validated_by_task_model: dict[tuple[TaskName, str], dict[str, StrictModel]] = defaultdict(dict)
    labels_by_task: dict[TaskName, list[GoldLabel]] = defaultdict(list)

    for task in selected_tasks:
        pairs = load_cases(task)
        if limit is not None:
            pairs = pairs[:limit]
        labels_by_task[task] = [gold for _case, gold in pairs]
        for model_name in selected_models:
            model = settings.models[model_name]
            adapter = OllamaAdapter(model_id=model.model_id, think=args.think)
            prompt_id, version, schema = TASK_PROMPTS[task][model_name]
            template = load(prompt_id, version)
            variables: dict[str, str] = {}
            if "{schema_description}" in template.user_template:
                variables["schema_description"] = schema_description(schema)

            for case, gold in pairs:
                request = CompletionRequest(
                    task=task,
                    case_id=case.id,
                    prompt_id=prompt_id,
                    prompt_version=version,
                    system=template.system,
                    user_content=render_user(
                        template,
                        variables,
                        untrusted=case.document_text,
                    ),
                    temperature=settings.temperature,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
                parsed: StrictModel | None
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
                    parsed = None
                    output = None
                    error = str(exc)
                    tries = settings.max_schema_repairs

                output_record = OutputRecord(
                    run_id=run_id,
                    task=task,
                    case_id=case.id,
                    model_name=model_name,
                    model_id=model.model_id,
                    prompt_version=version,
                    succeeded=output is not None,
                    repairs=tries,
                    output=output,
                    error=error,
                )
                if parsed is not None:
                    validated_by_task_model[(task, model_name)][case.id] = parsed
                gold_dict = gold.model_dump()
                case_scores = score_output(
                    output_record,
                    gold_dict,
                    source=case.document_text,
                )
                append_record(outputs_path, output_record)
                all_outputs.append(output_record)
                for score in case_scores:
                    append_record(scores_path, score)
                    all_scores.append(score)
                print(
                    f"{task:13} {model_name:8} {case.id:5} "
                    f"{'ok' if output_record.succeeded else 'failed'}"
                )

    for task in selected_tasks:
        if task == "triage":
            continue
        for model_name in selected_models:
            _add_version_scores(
                run_id=run_id,
                task=task,
                model_name=model_name,
                model_id=settings.models[model_name].model_id,
                labels=labels_by_task[task],
                outputs=validated_by_task_model[(task, model_name)],
                scores_path=scores_path,
                all_scores=all_scores,
            )

    write_reports(
        run_id=run_id,
        models=selected_models,
        usage=[],
        outputs=all_outputs,
        scores=all_scores,
        report_path=PROJECT_ROOT / "reports" / "comparison.md",
        decision_path=PROJECT_ROOT / "docs" / "model-decision.md",
    )
    print(f"Report: {PROJECT_ROOT / 'reports' / 'comparison.md'}")


if __name__ == "__main__":
    main()

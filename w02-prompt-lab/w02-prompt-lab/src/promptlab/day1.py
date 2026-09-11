from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from promptlab.config import PROJECT_ROOT, ModelConfig, Settings
from promptlab.usage import CallRecord, append_record, compute_cost

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


def generate(
    settings: Settings,
    prompt: str,
    *,
    temperature: float,
    num_predict: int,
) -> tuple[dict[str, Any], int]:
    model = settings.models["mistral"]
    started = time.perf_counter()
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": model.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        },
        timeout=180.0,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    return payload, latency_ms

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

    tiny_predict = 8
    truncation_run_id = f"{run_id}-truncation"
    prompt = render_prompt(template, e11["source"])
    payload, latency_ms = generate(
        settings,
        prompt,
        temperature=settings.temperature,
        num_predict=tiny_predict,
    )
    input_tokens = int(payload.get("prompt_eval_count") or 0)
    output_tokens = int(payload.get("eval_count") or 0)
    stop_reason = payload.get("done_reason")
    error_type = "TruncatedResponseError" if stop_reason == "length" else None
    response_text = payload.get("response")
    truncation = CallRecord(
        record_id=str(uuid.uuid4()),
        run_id=truncation_run_id,
        timestamp=datetime.now(UTC),
        provider="ollama",
        model_id=model.model_id,
        task="extraction",
        case_id="E11",
        prompt_id="baseline",
        prompt_version="v0",
        attempt=2,
        temperature=settings.temperature,
        max_output_tokens=tiny_predict,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=None,
        latency_ms=latency_ms,
        cost_usd=compute_cost(model.model_id, input_tokens, output_tokens),
        stop_reason=stop_reason,
        error_type=error_type,
        response_text=response_text,
    )
    append_record(truncation, truncation_run_id)
    print("E11 truncation", stop_reason, error_type, output_tokens)

def main() -> None:
    settings = Settings.from_env()
    model = settings.models["mistral"]
    run_id = str(uuid.uuid4())
    num_predict = 256
    template = PROMPT_PATH.read_text(encoding="utf-8")
    cases = load_cases(CASES_PATH, CASE_IDS)
    for case in cases:
        prompt = render_prompt(template, case["source"])
        payload, latency_ms = generate(
            settings,
            prompt,
            temperature=settings.temperature,
            num_predict=num_predict,
        )
        input_tokens = int(payload.get("prompt_eval_count") or 0)
        output_tokens = int(payload.get("eval_count") or 0)
        stop_reason = payload.get("done_reason")
        error_type = "TruncatedResponseError" if stop_reason == "length" else None
        response_text = payload.get("response")
        record = CallRecord(
            record_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp=datetime.now(UTC),
            provider="ollama",
            model_id=model.model_id,
            task="extraction",
            case_id=case["id"],
            prompt_id="baseline",
            prompt_version="v0",
            attempt=1,
            temperature=settings.temperature,
            max_output_tokens=num_predict,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=None,
            latency_ms=latency_ms,
            cost_usd=compute_cost(model.model_id, input_tokens, output_tokens),
            stop_reason=stop_reason,
            error_type=error_type,
            response_text=response_text,
        )
        append_record(record, run_id)
        print(case["id"], record.latency_ms, record.input_tokens, record.output_tokens)

    truncate_example(cases, run_id, template, settings, model)

if __name__ == "__main__":
    main()
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from promptlab.config import PROJECT_ROOT, Settings

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


def main() -> None:
    settings = Settings.from_env()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    cases = load_cases(CASES_PATH, CASE_IDS)
    for case in cases:
        prompt = render_prompt(template, case["source"])
        payload, latency_ms = generate(
            settings,
            prompt,
            temperature=0.0,
            num_predict=256,
        )
        input_tokens = int(payload.get("prompt_eval_count") or 0)
        output_tokens = int(payload.get("eval_count") or 0)
        stop_reason = str(payload.get("done_reason") or "")
        response_text = str(payload.get("response") or "")
        print(case["id"], latency_ms, input_tokens, output_tokens, stop_reason)
        print(response_text)

if __name__ == "__main__":
    main()
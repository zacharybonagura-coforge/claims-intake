import uuid
from promptlab.adapters.base import CompletionRequest
from promptlab.adapters.ollama import OllamaAdapter
from promptlab.config import PROJECT_ROOT, Settings
from promptlab.day1 import load_cases

CASES_PATH = PROJECT_ROOT / "cases" / "summarization.jsonl"
CASE_IDS = (
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
PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "baseline.v0.md"


def main() -> None:
    settings = Settings.from_env()
    run_id = str(uuid.uuid4())
    template = PROMPT_PATH.read_text(encoding="utf-8")
    system, _, _ = template.partition("<document>")
    cases = load_cases(CASES_PATH, CASE_IDS)
    adapters = (
        OllamaAdapter(model_id=settings.models["mistral"].model_id),
        OllamaAdapter(model_id=settings.models["qwen"].model_id),
    )

    print("run_id", run_id)

    cases = load_cases(CASES_PATH, CASE_IDS)
    for adapter in adapters:
        for case in cases:
            request = CompletionRequest(
                task="summarization",
                case_id=case["id"],
                prompt_id="baseline",
                prompt_version="v0",
                system=system.strip(),
                user_content=case["source"],
                temperature=settings.temperature,
                max_output_tokens=512,
            )
            result = adapter.complete(request, run_id)
            record = result.records[-1]
            print(
                adapter.model_id,
                case["id"],
                result.succeeded,
                result.error_type,
                record.input_tokens,
                record.output_tokens,
                record.latency_ms,
            )

if __name__ == "__main__":
    main()
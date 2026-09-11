from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

import httpx

from promptlab.adapters.base import CompletionRequest, CompletionResult
from promptlab.config import Settings
from promptlab.errors import (
    PermanentProviderError,
    TransientProviderError,
    TruncatedResponseError,
)
from promptlab.usage import CallRecord, append_record, compute_cost


class OllamaAdapter:
    provider = "ollama"

    def __init__(self, model_id: str) -> None:
        self.provider = "ollama"
        self.model_id = model_id
        self._settings = Settings.from_env()

    def complete(self, request: CompletionRequest, run_id: str) -> CompletionResult:
        records: list[CallRecord] = []
        max_attempts = self._settings.max_retries + 1
        succeeded = False
        text: str | None = None
        error_type: str | None = None

        for attempt in range(1, max_attempts + 1):
            started = time.perf_counter()
            stop_reason: str | None = None
            input_tokens = 0
            output_tokens = 0
            text = None
            error_type = None
            succeeded = False

            try:
                response = httpx.post(
                    f"{self._settings.ollama_base_url}/api/generate",
                    json={
                        "model": self.model_id,
                        "prompt": request.user_content,
                        "system": request.system,
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "num_predict": request.max_output_tokens,
                        },
                    },
                    timeout=180.0,
                )
                if response.status_code >= 500:
                    raise TransientProviderError(f"HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise PermanentProviderError(f"HTTP {response.status_code}")

                payload = response.json()
                text = str(payload.get("response") or payload.get("message", {}).get("content") or "")
                input_tokens = int(payload.get("prompt_eval_count") or 0)
                output_tokens = int(payload.get("eval_count") or 0)
                stop_reason = payload.get("done_reason")
                if stop_reason == "length":
                    raise TruncatedResponseError("output token ceiling reached")
                succeeded = True
            except (httpx.ConnectError, httpx.TimeoutException, TransientProviderError) as exc:
                error_type = TransientProviderError.__name__
            except PermanentProviderError:
                error_type = PermanentProviderError.__name__
            except TruncatedResponseError:
                error_type = TruncatedResponseError.__name__

            latency_ms = int((time.perf_counter() - started) * 1000)
            record = CallRecord(
                record_id=str(uuid.uuid4()),
                run_id=run_id,
                timestamp=datetime.now(UTC),
                provider="ollama",
                model_id=self.model_id,
                task=request.task,
                case_id=request.case_id,
                prompt_id=request.prompt_id,
                prompt_version=request.prompt_version,
                attempt=attempt,
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=None,
                latency_ms=latency_ms,
                cost_usd=compute_cost(self.model_id, input_tokens, output_tokens),
                stop_reason=stop_reason,
                error_type=error_type,
                response_text=text,
            )
            append_record(record, run_id)
            records.append(record)

            if succeeded or error_type != TransientProviderError.__name__:
                break
            if attempt < max_attempts:
                time.sleep(0.1 * (2 ** (attempt - 1)))

        return CompletionResult(
            succeeded=succeeded,
            text=text,
            error_type=error_type,
            records=records,
        )
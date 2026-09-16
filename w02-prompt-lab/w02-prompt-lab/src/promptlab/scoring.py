"""Deterministic Day 4 triage scoring. Does not call a model."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from promptlab.config import PROJECT_ROOT
from promptlab.records import OutputRecord, ScoreRecord

SCORER_VERSION = "day4.v1"
GOLD_PATH = PROJECT_ROOT / "cases" / "gold" / "triage.jsonl"
BOUNDARY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(has been|have been|is|was|will be)\s+"
        r"(approved|denied|rejected|resolved|closed|granted)\b",
        re.I,
    ),
    re.compile(r"\b(will be|have been|has been)\s+refund", re.I),
    re.compile(r"\breimburs", re.I),
    re.compile(r"\bfunds will be\b", re.I),
    re.compile(r"\bloan was granted\b", re.I),
)


def load_gold(path: Path = GOLD_PATH) -> dict[str, dict[str, Any]]:
    gold: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        gold[str(row["id"])] = row
    return gold


def _boundary_ok(output: dict[str, Any] | None) -> tuple[bool, str | None]:
    if output is None:
        return False, "no output"
    if output.get("customer_outcome") is not None:
        return False, "customer_outcome is not null"
    text = str(output.get("draft_reply") or "")
    for pattern in BOUNDARY_PATTERNS:
        match = pattern.search(text)
        if match:
            return False, match.group(0)
    return True, None


def score_output(record: OutputRecord, gold: dict[str, Any]) -> list[ScoreRecord]:
    """Score one triage output against gold. Never calls a model."""
    output = record.output
    expected_queue = gold["expected_queue"]
    expected_escalation = bool(gold["expected_escalation"])
    predicted_queue = None if output is None else output.get("queue")
    predicted_escalation = None if output is None else output.get("escalation_required")

    queue_ok = predicted_queue == expected_queue
    escalation_ok = predicted_escalation is True if expected_escalation \
        else predicted_escalation is False
    missed = expected_escalation and predicted_escalation is False
    unnecessary = (not expected_escalation) and predicted_escalation is True
    boundary_ok, boundary_detail = _boundary_ok(output)

    def make(
        metric: str,
        numerator: int,
        *,
        lower_is_better: bool = False,
        detail: str | None = None,
    ) -> ScoreRecord:
        return ScoreRecord(
            run_id=record.run_id,
            task=record.task,
            case_id=record.case_id,
            model_name=record.model_name,
            prompt_version=record.prompt_version,
            scorer_version=SCORER_VERSION,
            metric=metric,
            numerator=numerator,
            denominator=1,
            lower_is_better=lower_is_better,
            detail=detail,
        )

    return [
        make("queue", int(queue_ok), detail=f"pred={predicted_queue} gold={expected_queue}"),
        make("escalation_required", int(escalation_ok), 
            detail=f"pred={predicted_escalation} gold={expected_escalation}"),
        make("missed_escalation", int(missed), lower_is_better=True),
        make("unnecessary_escalation", int(unnecessary), lower_is_better=True),
        make("human_boundary", int(boundary_ok), detail=boundary_detail),
    ]
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from promptlab.config import PROJECT_ROOT

CASE_IDS = ("E12", "E07", "E11")
CASES_PATH = PROJECT_ROOT / "cases" / "extraction.jsonl"


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


def main() -> None:
    cases = load_cases(CASES_PATH, CASE_IDS)
    for case in cases:
        print(case["id"], len(case["source"]))


if __name__ == "__main__":
    main()
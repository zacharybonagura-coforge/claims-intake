from __future__ import annotations

import json
import re

from promptlab.config import PROJECT_ROOT

OUTPUT_PATH = PROJECT_ROOT / "docs" / "day3-run.jsonl"
CASE_FILES = (
    PROJECT_ROOT / "cases" / "summarization.jsonl",
    PROJECT_ROOT / "cases" / "extraction.jsonl",
)

MARKERS = (
    "Northglass",
    "Norwyn",
    "Bellwater",
    "Larkspur",
    "Meadowcross",
    "2026-02-10",
    "2026-05-09",
    "Release 14.2",
)


def headings(source: str) -> list[str]:
    return [
        line.strip()
        for line in source.splitlines()
        if re.match(r"^\d+\.\s+\S", line.strip())
    ]


def present_fields(output: dict[str, object]) -> list[tuple[str, str | None]]:
    fields: list[tuple[str, str | None]] = []
    for name, value in output.items():
        if name == "document_status" or not isinstance(value, dict):
            continue
        if value.get("status") == "present":
            fields.append((name, value.get("citation")))
    return fields


def load_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in CASE_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            sources[row["id"]] = row["source"]
    return sources


def main() -> None:
    count = 0
    for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["task"] != "extraction" or row["output"] is None:
            continue
        blob = json.dumps(row["output"])
        hits = [m for m in MARKERS if m in blob]
        if hits:
            count += 1
            print(row["case_id"], hits)
    print("Leakage count", count)

    sources = load_sources()
    citation_failures = 0
    for line in OUTPUT_PATH.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["output"] is None:
            continue
        found = headings(sources[row["case_id"]])
        for name, citation in present_fields(row["output"]):
            ok = isinstance(citation, str) and any(citation in heading for heading in found)
            if not ok:
                citation_failures += 1
                print(row["case_id"], name, repr(citation), "not in", found)
    print("Citation-existence failure count", citation_failures)


if __name__ == "__main__":
    main()
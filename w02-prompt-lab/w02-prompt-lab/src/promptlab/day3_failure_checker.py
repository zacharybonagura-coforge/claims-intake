import json
import re
from pathlib import Path

# Step 7

markers = (
    "Northglass",
    "Norwyn",
    "Bellwater",
    "Larkspur",
    "Meadowcross",
    "2026-02-10",
    "2026-05-09",
    "Release 14.2",
)

count = 0
for line in Path("w02-prompt-lab/docs/day3-run.jsonl").read_text().splitlines():
    row = json.loads(line)
    if row["task"] != "extraction" or row["output"] is None:
        continue
    blob = json.dumps(row["output"])
    hits = [m for m in markers if m in blob]
    if hits:
        count += 1
        print(row["case_id"], hits)

print("Leakage count", count)


# Step 8

CASE_FILES = (
    Path("w02-prompt-lab/cases/summarization.jsonl"),
    Path("w02-prompt-lab/cases/extraction.jsonl"),
)


def load_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in CASE_FILES:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            sources[row["id"]] = row["source"]
    return sources


def headings(source: str) -> list[str]:
    # Numbered section titles only
    return [
        line.strip()
        for line in source.splitlines()
        if re.match(r"^\d+\.\s+\S", line.strip())
    ]


def present_fields(output: dict[str, object]) -> list[tuple[str, str | None]]:
    # Get evidence fields the model marked present
    fields: list[tuple[str, str | None]] = []
    for name, value in output.items():
        if name == "document_status" or not isinstance(value, dict):
            continue
        if value.get("status") == "present":
            fields.append((name, value.get("citation")))
    return fields


sources = load_sources()
citation_failures = 0
for line in Path("w02-prompt-lab/docs/day3-run.jsonl").read_text().splitlines():
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

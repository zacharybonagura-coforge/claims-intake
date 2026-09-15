from __future__ import annotations

from promptlab.day3 import EXTRACTION_IDS, SUMMARIZATION_IDS, render_prompt
from promptlab.schemas import PolicyExtraction, SummarizationOutput, schema_description


def test_day3_covers_twelve_cases_each() -> None:
    assert len(SUMMARIZATION_IDS) == 12
    assert len(EXTRACTION_IDS) == 12
    assert SUMMARIZATION_IDS[0] == "S01"
    assert EXTRACTION_IDS[-1] == "E12"


def test_render_prompt_fills_extract_placeholders() -> None:
    template = "DOC\n{document_text}\nSCHEMA\n{schema_description}\n"
    rendered = render_prompt(template, "hello source", PolicyExtraction)
    assert "hello source" in rendered
    assert "{document_text}" not in rendered
    assert "{schema_description}" not in rendered
    assert "PolicyExtraction" in rendered or "policy_name" in rendered


def test_render_prompt_appends_schema_when_placeholder_missing() -> None:
    rendered = render_prompt("only {document_text}", "body", SummarizationOutput)
    assert "body" in rendered
    assert schema_description(SummarizationOutput) in rendered
    assert "Return only a JSON object" in rendered

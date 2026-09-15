from __future__ import annotations

from promptlab.day3_failure_checker import headings, present_fields


def test_headings_keeps_numbered_titles_only() -> None:
    source = (
        "1. Document Control\n"
        "Title: Example. Version: 1.0.\n"
        "2. Purpose\n"
        "Body text.\n"
    )
    assert headings(source) == ["1. Document Control", "2. Purpose"]


def test_present_fields_skips_document_status_and_absent() -> None:
    output: dict[str, object] = {
        "document_status": "valid",
        "title": {"value": "X", "status": "present", "citation": "1. Document Control"},
        "version": {"value": None, "status": "absent", "citation": None},
    }
    assert present_fields(output) == [("title", "1. Document Control")]


def test_present_citation_matches_heading() -> None:
    found = headings("1. Document Control\n2. Purpose\n")
    citation = "1. Document Control"
    assert any(citation in heading for heading in found)


def test_version_string_is_not_a_heading() -> None:
    found = headings("1. Document Control\nTitle: X. Version: 1.0.\n")
    citation = "1.0"
    assert not any(citation in heading for heading in found)

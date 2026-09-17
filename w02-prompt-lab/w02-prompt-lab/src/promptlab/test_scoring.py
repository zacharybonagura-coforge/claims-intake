from promptlab.corpus import GoldLabel
from promptlab.records import OutputRecord
from promptlab.schemas import EvidenceField, PolicyExtraction, TriageOutput
from promptlab.scoring import score_output, source_sections


def _record(*, task: str, case_id: str, output) -> OutputRecord:
    return OutputRecord(
        run_id="test",
        task=task,
        case_id=case_id,
        model_name="test",
        model_id="test",
        prompt_version="v1",
        succeeded=True,
        repairs=0,
        output=output.model_dump(),
        error=None,
    )


def test_source_sections_reads_numbered_headings() -> None:
    assert source_sections("1. Document Control\nBody\n2. Scope\nText") == {
        "1. document control",
        "2. scope",
    }


def test_evidence_recall_citations_and_unsupported_avoidance() -> None:
    output = PolicyExtraction(
        document_status="valid",
        policy_name=EvidenceField(
            value="Test Policy", status="present", citation="1. Document Control"
        ),
        version=EvidenceField(value="1.0", status="present", citation="1. Document Control"),
        effective_date=EvidenceField(value=None, status="absent"),
        jurisdictions=EvidenceField(value="Pennsylvania", status="present", citation="2. Scope"),
        beneficial_ownership_threshold=EvidenceField(value=None, status="absent"),
        review_frequency=EvidenceField(value="12 months", status="present", citation="4. Review"),
        required_documents=EvidenceField(value=None, status="absent"),
    )
    gold = GoldLabel(
        id="E00",
        task="extraction",
        expected_status="valid",
        recoverable_fields=["policy_name", "version", "jurisdictions", "review_frequency"],
    )
    scores = score_output(
        _record(task="extraction", case_id="E00", output=output),
        gold.model_dump(),
        source=(
            "1. Document Control\nTest Policy 1.0\n2. Scope\nPennsylvania\n"
            "4. Review\n12 months"
        ),
    )
    by_metric = {score.metric: score for score in scores}
    assert by_metric["required_evidence_recall"].numerator == 4
    assert by_metric["required_evidence_recall"].denominator == 4
    assert by_metric["citation_correctness"].numerator == 4
    assert by_metric["citation_correctness"].denominator == 4


def test_triage_detects_pii_leakage_and_boundary_violation() -> None:
    output = TriageOutput(
        queue="fraud_report",
        escalation_required=False,
        confidence=0.9,
        rationale="Unauthorized activity",
        draft_reply="Your claim has been approved. Call 215-555-0148.",
        human_review_required=True,
        customer_outcome=None,
    )
    gold = GoldLabel(
        id="T00",
        task="triage",
        expected_queue="fraud_report",
        expected_escalation=False,
    )
    scores = score_output(
        _record(task="triage", case_id="T00", output=output),
        gold.model_dump(),
        source="Unauthorized purchase",
    )
    by_metric = {score.metric: score for score in scores}
    assert by_metric["pii_leakage"].numerator == 1
    assert by_metric["pii_leakage"].lower_is_better
    assert by_metric["human_boundary"].numerator == 0
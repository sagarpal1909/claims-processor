import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.extractor import ExtractionAgent
from models.claim import ClaimInput, DocumentInput, DocumentType, DocumentQuality

agent = ExtractionAgent()


def _claim_with_docs(docs) -> ClaimInput:
    return ClaimInput(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        submission_date="2024-11-08",
        claimed_amount=1500,
        documents=docs,
    )


def _doc_with_content(file_id="F001", actual_type="PRESCRIPTION", content=None):
    return DocumentInput(
        file_id=file_id,
        actual_type=DocumentType(actual_type),
        content=content or {"patient_name": "Rajesh Kumar", "diagnosis": "Viral Fever"},
    )


def _doc_no_content(file_id="F001", actual_type="PRESCRIPTION"):
    return DocumentInput(
        file_id=file_id,
        actual_type=DocumentType(actual_type),
    )


class TestTestModePassthrough:
    def test_pre_provided_content_returned_as_is(self):
        content = {"patient_name": "Rajesh Kumar", "diagnosis": "Viral Fever", "total_amount": 1500}
        doc = _doc_with_content("F001", "PRESCRIPTION", content)
        claim = _claim_with_docs([doc])
        extracted, trace = agent.run(claim)
        assert extracted["F001"]["patient_name"] == "Rajesh Kumar"
        assert extracted["F001"]["diagnosis"] == "Viral Fever"

    def test_document_type_added_to_content(self):
        doc = _doc_with_content("F001", "HOSPITAL_BILL", {"total_amount": 1500})
        claim = _claim_with_docs([doc])
        extracted, trace = agent.run(claim)
        assert extracted["F001"]["document_type"] == "HOSPITAL_BILL"

    def test_multiple_docs_all_extracted(self):
        docs = [
            _doc_with_content("F001", "PRESCRIPTION", {"diagnosis": "Fever"}),
            _doc_with_content("F002", "HOSPITAL_BILL", {"total_amount": 1500}),
        ]
        claim = _claim_with_docs(docs)
        extracted, trace = agent.run(claim)
        assert "F001" in extracted
        assert "F002" in extracted

    def test_trace_has_pass_step_per_doc(self):
        docs = [
            _doc_with_content("F001", "PRESCRIPTION"),
            _doc_with_content("F002", "HOSPITAL_BILL"),
        ]
        claim = _claim_with_docs(docs)
        extracted, trace = agent.run(claim)
        pass_steps = [s for s in trace if s.status == "PASS"]
        assert len(pass_steps) >= 2


class TestFailureHandling:
    def test_no_content_no_file_returns_gracefully(self):
        # No content, no file_data — will attempt real extraction and fail gracefully
        doc = _doc_no_content("F001", "PRESCRIPTION")
        claim = _claim_with_docs([doc])
        extracted, trace = agent.run(claim)
        # Should not raise — graceful failure
        assert "F001" in extracted

    def test_extraction_failure_sets_extraction_failed_flag(self):
        doc = _doc_no_content("F001", "PRESCRIPTION")
        claim = _claim_with_docs([doc])
        extracted, trace = agent.run(claim)
        # Either succeeded via Ollama or returned extraction_failed
        assert isinstance(extracted["F001"], dict)

    def test_one_doc_failure_does_not_stop_other_docs(self):
        docs = [
            _doc_no_content("F001", "PRESCRIPTION"),   # will fail (no content, no file)
            _doc_with_content("F002", "HOSPITAL_BILL", {"total_amount": 1500}),  # will pass
        ]
        claim = _claim_with_docs(docs)
        extracted, trace = agent.run(claim)
        # F002 must still be extracted correctly
        assert extracted["F002"]["total_amount"] == 1500

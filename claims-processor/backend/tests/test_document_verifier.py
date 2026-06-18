import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.document_verifier import DocumentVerifierAgent, DocumentVerificationError
from models.claim import ClaimInput, DocumentInput, DocumentQuality, DocumentType
from models.decision import RejectionReason


def _claim(**kwargs) -> ClaimInput:
    defaults = dict(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        submission_date="2024-11-08",
        claimed_amount=1500,
    )
    defaults.update(kwargs)
    return ClaimInput(**defaults)


def _doc(file_id="F001", actual_type="PRESCRIPTION", quality="GOOD", patient_name=None):
    return DocumentInput(
        file_id=file_id,
        actual_type=DocumentType(actual_type),
        quality=DocumentQuality(quality),
        patient_name_on_doc=patient_name,
    )


agent = DocumentVerifierAgent()


class TestUnreadableCheck:
    def test_unreadable_doc_raises(self):
        claim = _claim(documents=[_doc(quality="UNREADABLE")])
        with pytest.raises(DocumentVerificationError) as exc:
            agent.run(claim)
        assert exc.value.reason == RejectionReason.UNREADABLE_DOCUMENT

    def test_good_quality_passes(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION", "GOOD"),
            _doc("F002", "HOSPITAL_BILL", "GOOD"),
        ])
        trace = agent.run(claim)
        assert any(s.step == "readability_check" and s.status == "PASS" for s in trace)


class TestDocumentTypeCheck:
    def test_wrong_type_raises(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION"),
            _doc("F002", "PRESCRIPTION"),  # should be HOSPITAL_BILL
        ])
        with pytest.raises(DocumentVerificationError) as exc:
            agent.run(claim)
        assert exc.value.reason == RejectionReason.WRONG_DOCUMENT_TYPE

    def test_correct_types_pass(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION"),
            _doc("F002", "HOSPITAL_BILL"),
        ])
        trace = agent.run(claim)
        assert any(s.step == "type_check" and s.status == "PASS" for s in trace)

    def test_pharmacy_requires_pharmacy_bill(self):
        claim = _claim(claim_category="PHARMACY", documents=[
            _doc("F001", "PRESCRIPTION"),
            _doc("F002", "HOSPITAL_BILL"),  # wrong — should be PHARMACY_BILL
        ])
        with pytest.raises(DocumentVerificationError) as exc:
            agent.run(claim)
        assert exc.value.reason == RejectionReason.WRONG_DOCUMENT_TYPE

    def test_dental_only_needs_hospital_bill(self):
        claim = _claim(claim_category="DENTAL", documents=[
            _doc("F001", "HOSPITAL_BILL"),
        ])
        trace = agent.run(claim)
        assert any(s.step == "type_check" and s.status == "PASS" for s in trace)


class TestPatientConsistencyCheck:
    def test_different_patient_names_raises(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION", patient_name="Rajesh Kumar"),
            _doc("F002", "HOSPITAL_BILL", patient_name="Arjun Mehta"),
        ])
        with pytest.raises(DocumentVerificationError) as exc:
            agent.run(claim)
        assert exc.value.reason == RejectionReason.CROSS_PATIENT_MISMATCH

    def test_same_patient_name_passes(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION", patient_name="Rajesh Kumar"),
            _doc("F002", "HOSPITAL_BILL", patient_name="Rajesh Kumar"),
        ])
        trace = agent.run(claim)
        assert any(s.step == "patient_consistency_check" and s.status == "PASS" for s in trace)

    def test_single_named_doc_skips_check(self):
        claim = _claim(documents=[
            _doc("F001", "PRESCRIPTION", patient_name="Rajesh Kumar"),
            _doc("F002", "HOSPITAL_BILL"),  # no name
        ])
        trace = agent.run(claim)
        assert any(s.step == "patient_consistency_check" and s.status == "INFO" for s in trace)

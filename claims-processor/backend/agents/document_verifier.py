"""
Document Verifier Agent

Runs before any processing. Checks:
1. Correct document types are present for the claim category
2. No document is unreadable
3. All documents belong to the same patient
"""
from __future__ import annotations
from typing import Optional

from models.claim import ClaimInput, DocumentType, DocumentQuality
from models.decision import TraceStep, RejectionReason

REQUIRED_DOCS: dict[str, list[str]] = {
    "CONSULTATION":         ["PRESCRIPTION", "HOSPITAL_BILL"],
    "DIAGNOSTIC":           ["PRESCRIPTION", "LAB_REPORT", "HOSPITAL_BILL"],
    "PHARMACY":             ["PRESCRIPTION", "PHARMACY_BILL"],
    "DENTAL":               ["HOSPITAL_BILL"],
    "VISION":               ["PRESCRIPTION", "HOSPITAL_BILL"],
    "ALTERNATIVE_MEDICINE": ["PRESCRIPTION", "HOSPITAL_BILL"],
}


class DocumentVerificationError(Exception):
    """Raised when documents fail verification — pipeline must stop."""
    def __init__(self, message: str, reason: RejectionReason, trace: list[TraceStep]):
        super().__init__(message)
        self.reason = reason
        self.trace = trace


class DocumentVerifierAgent:
    """
    Input : ClaimInput
    Output: list[TraceStep]  (appended to the shared trace on success)
    Raises: DocumentVerificationError on any hard failure
    """

    def run(self, claim: ClaimInput) -> list[TraceStep]:
        trace: list[TraceStep] = []

        trace.append(TraceStep(
            agent="DocumentVerifier",
            step="start",
            status="INFO",
            detail=f"Verifying {len(claim.documents)} document(s) for {claim.claim_category} claim",
        ))

        self._check_unreadable(claim, trace)
        self._check_required_types(claim, trace)
        self._check_patient_consistency(claim, trace)

        trace.append(TraceStep(
            agent="DocumentVerifier",
            step="complete",
            status="PASS",
            detail="All document checks passed",
        ))
        return trace

    # ------------------------------------------------------------------
    def _check_unreadable(self, claim: ClaimInput, trace: list[TraceStep]) -> None:
        for doc in claim.documents:
            if doc.quality == DocumentQuality.UNREADABLE:
                msg = (
                    f"The document '{doc.file_name or doc.file_id}' "
                    f"(type: {doc.actual_type or 'unknown'}) could not be read — "
                    "the image is too blurry or damaged. "
                    "Please re-upload a clear, well-lit photo of this document."
                )
                trace.append(TraceStep(
                    agent="DocumentVerifier",
                    step="readability_check",
                    status="FAIL",
                    detail=msg,
                    data={"file_id": doc.file_id, "file_name": doc.file_name},
                ))
                raise DocumentVerificationError(msg, RejectionReason.UNREADABLE_DOCUMENT, trace)

        trace.append(TraceStep(
            agent="DocumentVerifier",
            step="readability_check",
            status="PASS",
            detail="All documents are readable",
        ))

    def _check_required_types(self, claim: ClaimInput, trace: list[TraceStep]) -> None:
        required = REQUIRED_DOCS.get(claim.claim_category, [])
        uploaded_types = [
            doc.actual_type.value if doc.actual_type else "UNKNOWN"
            for doc in claim.documents
        ]

        missing: list[str] = []
        for req in required:
            if req not in uploaded_types:
                missing.append(req)

        wrong: list[str] = []
        for utype in uploaded_types:
            if utype not in required and utype != "UNKNOWN":
                # only flag as "wrong" if it's not an optional type for this category
                wrong.append(utype)

        if missing:
            missing_str = ", ".join(missing)
            wrong_str = ", ".join(wrong) if wrong else "an unrecognised document"
            msg = (
                f"Your {claim.claim_category} claim is missing required document(s): "
                f"{missing_str}. "
                f"You uploaded: {', '.join(uploaded_types)}. "
                f"Please provide the missing document(s) and resubmit."
            )
            if wrong:
                msg = (
                    f"Incorrect document uploaded for a {claim.claim_category} claim. "
                    f"You uploaded {wrong_str}, but this claim type requires: {', '.join(required)}. "
                    f"Missing: {missing_str}. "
                    "Please replace the incorrect document with the required one."
                )
            trace.append(TraceStep(
                agent="DocumentVerifier",
                step="type_check",
                status="FAIL",
                detail=msg,
                data={"required": required, "uploaded": uploaded_types, "missing": missing, "wrong": wrong},
            ))
            raise DocumentVerificationError(msg, RejectionReason.WRONG_DOCUMENT_TYPE, trace)

        trace.append(TraceStep(
            agent="DocumentVerifier",
            step="type_check",
            status="PASS",
            detail=f"All required document types present: {required}",
            data={"required": required, "uploaded": uploaded_types},
        ))

    def _check_patient_consistency(self, claim: ClaimInput, trace: list[TraceStep]) -> None:
        named_docs: list[tuple[str, str]] = []  # (file_id, patient_name)

        for doc in claim.documents:
            name: Optional[str] = None
            if doc.patient_name_on_doc:
                name = doc.patient_name_on_doc.strip()
            elif doc.content and doc.content.get("patient_name"):
                name = str(doc.content["patient_name"]).strip()

            if name:
                named_docs.append((doc.file_id, name))

        if len(named_docs) < 2:
            trace.append(TraceStep(
                agent="DocumentVerifier",
                step="patient_consistency_check",
                status="INFO",
                detail="Not enough named documents to cross-check patient identity",
            ))
            return

        unique_names = {n.lower() for _, n in named_docs}
        if len(unique_names) > 1:
            details = ", ".join(f"{fid} → '{nm}'" for fid, nm in named_docs)
            msg = (
                "The documents you uploaded appear to belong to different patients. "
                f"Patient names found: {details}. "
                "Please ensure all documents are for the same patient and resubmit."
            )
            trace.append(TraceStep(
                agent="DocumentVerifier",
                step="patient_consistency_check",
                status="FAIL",
                detail=msg,
                data={"names_found": dict(named_docs)},
            ))
            raise DocumentVerificationError(msg, RejectionReason.CROSS_PATIENT_MISMATCH, trace)

        trace.append(TraceStep(
            agent="DocumentVerifier",
            step="patient_consistency_check",
            status="PASS",
            detail=f"Patient name consistent across all documents: '{named_docs[0][1]}'",
        ))

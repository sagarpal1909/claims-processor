from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ClaimCategory(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    UNKNOWN = "UNKNOWN"


class DocumentQuality(str, Enum):
    GOOD = "GOOD"
    POOR = "POOR"
    UNREADABLE = "UNREADABLE"


class DocumentInput(BaseModel):
    file_id: str
    file_name: str = ""
    actual_type: Optional[DocumentType] = None   # provided in test mode
    quality: DocumentQuality = DocumentQuality.GOOD
    content: Optional[dict[str, Any]] = None      # pre-extracted content (test mode)
    patient_name_on_doc: Optional[str] = None
    file_data: Optional[str] = None               # base64-encoded file content
    file_media_type: Optional[str] = None         # e.g. "image/jpeg", "application/pdf"


class ClaimsHistoryEntry(BaseModel):
    claim_id: str
    date: str
    amount: float
    provider: str


class ClaimInput(BaseModel):
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: str
    claimed_amount: float
    hospital_name: Optional[str] = None
    submission_date: Optional[str] = None  # ISO 8601; defaults to today if absent
    ytd_claims_amount: float = 0.0
    claims_history: list[ClaimsHistoryEntry] = Field(default_factory=list)
    documents: list[DocumentInput] = Field(default_factory=list)
    simulate_component_failure: bool = False

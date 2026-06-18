from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RejectionReason(str, Enum):
    WAITING_PERIOD = "WAITING_PERIOD"
    PRE_AUTH_MISSING = "PRE_AUTH_MISSING"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    SUB_LIMIT_EXCEEDED = "SUB_LIMIT_EXCEEDED"
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    DOCUMENT_MISMATCH = "DOCUMENT_MISMATCH"
    WRONG_DOCUMENT_TYPE = "WRONG_DOCUMENT_TYPE"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"
    CROSS_PATIENT_MISMATCH = "CROSS_PATIENT_MISMATCH"
    FRAUD_SIGNAL = "FRAUD_SIGNAL"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"


class TraceStep(BaseModel):
    agent: str
    step: str
    status: str                         # "PASS" | "FAIL" | "WARN" | "INFO" | "ERROR"
    detail: str
    data: Optional[dict[str, Any]] = None


class LineItemDecision(BaseModel):
    description: str
    claimed_amount: float
    approved_amount: float
    status: str                         # "APPROVED" | "REJECTED"
    reason: Optional[str] = None


class ClaimDecision(BaseModel):
    claim_id: str
    member_id: str
    status: DecisionStatus
    claimed_amount: float
    approved_amount: float = 0.0
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    message: str = ""
    line_items: list[LineItemDecision] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    trace: list[TraceStep] = Field(default_factory=list)
    component_failures: list[str] = Field(default_factory=list)
    manual_review_recommended: bool = False
    fraud_signals: list[str] = Field(default_factory=list)
    financial_breakdown: Optional[dict[str, Any]] = None

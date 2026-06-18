import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.policy_engine import PolicyEngineAgent
from models.claim import ClaimInput, DocumentInput, DocumentType
from models.decision import RejectionReason

agent = PolicyEngineAgent()


def _claim(**kwargs) -> ClaimInput:
    defaults = dict(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        submission_date="2024-11-08",
        claimed_amount=1500,
        ytd_claims_amount=0,
    )
    defaults.update(kwargs)
    return ClaimInput(**defaults)


def _run(claim, extracted=None):
    return agent.run(claim, extracted or {})


class TestMemberValidation:
    def test_unknown_member_rejected(self):
        result = _run(_claim(member_id="UNKNOWN"))
        assert RejectionReason.MEMBER_NOT_FOUND in result.rejection_reasons

    def test_valid_member_passes(self):
        result = _run(_claim())
        assert RejectionReason.MEMBER_NOT_FOUND not in result.rejection_reasons


class TestSubmissionDeadline:
    def test_late_submission_rejected(self):
        result = _run(_claim(treatment_date="2024-11-01", submission_date="2025-06-01"))
        assert RejectionReason.WAITING_PERIOD in result.rejection_reasons

    def test_on_time_submission_passes(self):
        result = _run(_claim(treatment_date="2024-11-01", submission_date="2024-11-08"))
        steps = {s.step: s.status for s in result.trace}
        assert steps.get("submission_deadline") == "PASS"


class TestMinimumClaimAmount:
    def test_below_minimum_rejected(self):
        result = _run(_claim(claimed_amount=400))
        assert RejectionReason.PER_CLAIM_EXCEEDED in result.rejection_reasons

    def test_at_minimum_passes(self):
        result = _run(_claim(claimed_amount=500))
        steps = {s.step: s.status for s in result.trace}
        assert steps.get("minimum_claim_amount") == "PASS"


class TestInitialWaitingPeriod:
    def test_within_waiting_period_rejected(self):
        # EMP005 joined 2024-09-01, treatment 2024-09-10 is within 30 days
        result = _run(_claim(member_id="EMP005", treatment_date="2024-09-10", submission_date="2024-09-17"))
        assert RejectionReason.WAITING_PERIOD in result.rejection_reasons

    def test_after_waiting_period_passes(self):
        result = _run(_claim(member_id="EMP001", treatment_date="2024-11-01", submission_date="2024-11-08"))
        steps = {s.step: s.status for s in result.trace}
        assert steps.get("initial_waiting_period") == "PASS"


class TestSpecificWaitingPeriods:
    def test_diabetes_within_waiting_period_rejected(self):
        extracted = {"F001": {"diagnosis": "Type 2 Diabetes Mellitus", "medicines": ["Metformin 500mg"]}}
        # EMP005 joined 2024-09-01, diabetes has 90-day wait, eligible from 2024-11-30
        result = _run(_claim(member_id="EMP005", treatment_date="2024-10-15", submission_date="2024-10-22"), extracted)
        assert RejectionReason.WAITING_PERIOD in result.rejection_reasons

    def test_no_condition_keywords_passes(self):
        extracted = {"F001": {"diagnosis": "Viral Fever", "medicines": ["Paracetamol"]}}
        result = _run(_claim(), extracted)
        steps = {s.step: s.status for s in result.trace}
        assert steps.get("specific_waiting_periods") == "PASS"


class TestExclusions:
    def test_bariatric_excluded(self):
        extracted = {"F001": {"diagnosis": "Morbid Obesity", "treatment": "Bariatric Surgery"}}
        result = _run(_claim(), extracted)
        assert RejectionReason.EXCLUDED_CONDITION in result.rejection_reasons

    def test_cosmetic_excluded(self):
        extracted = {"F001": {"treatment": "Cosmetic procedure"}}
        result = _run(_claim(), extracted)
        assert RejectionReason.EXCLUDED_CONDITION in result.rejection_reasons

    def test_covered_treatment_passes(self):
        extracted = {"F001": {"diagnosis": "Viral Fever"}}
        result = _run(_claim(), extracted)
        assert RejectionReason.EXCLUDED_CONDITION not in result.rejection_reasons


class TestPerClaimLimit:
    def test_exceeds_per_claim_limit(self):
        result = _run(_claim(claimed_amount=7500))
        assert RejectionReason.PER_CLAIM_EXCEEDED in result.rejection_reasons

    def test_within_per_claim_limit(self):
        result = _run(_claim(claimed_amount=4000))
        assert RejectionReason.PER_CLAIM_EXCEEDED not in result.rejection_reasons

    def test_dental_skips_per_claim_check(self):
        result = _run(_claim(claim_category="DENTAL", claimed_amount=9000))
        steps = {s.step: s.status for s in result.trace}
        assert steps.get("per_claim_limit") == "INFO"


class TestFamilyFloaterLimit:
    def test_exceeds_family_floater_limit(self):
        result = _run(_claim(ytd_claims_amount=148000, claimed_amount=5000))
        assert RejectionReason.ANNUAL_LIMIT_EXCEEDED in result.rejection_reasons

    def test_within_family_floater_limit(self):
        result = _run(_claim(ytd_claims_amount=10000, claimed_amount=5000))
        assert RejectionReason.ANNUAL_LIMIT_EXCEEDED not in result.rejection_reasons


class TestFraudSignals:
    def test_same_day_claims_trigger_fraud(self):
        from models.claim import ClaimsHistoryEntry
        history = [
            ClaimsHistoryEntry(claim_id=f"C00{i}", date="2024-11-01", amount=1000, provider="Clinic")
            for i in range(3)
        ]
        result = _run(_claim(claims_history=history))
        assert len(result.fraud_signals) > 0

    def test_high_value_triggers_fraud(self):
        result = _run(_claim(claimed_amount=30000))
        assert len(result.fraud_signals) > 0

    def test_clean_claim_no_fraud(self):
        result = _run(_claim(claimed_amount=1500))
        assert result.fraud_signals == []


class TestFinancialCalculation:
    def test_copay_applied(self):
        result = _run(_claim(claimed_amount=1500))
        assert result.approved_amount == 1350.0  # 10% copay on consultation

    def test_network_discount_applied_before_copay(self):
        result = _run(_claim(claimed_amount=4500, hospital_name="Apollo Hospitals"))
        assert result.approved_amount == 3240.0  # 20% discount then 10% copay

    def test_no_approval_on_rejection(self):
        result = _run(_claim(member_id="UNKNOWN"))
        assert result.approved_amount == 0.0

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.decision_agent import DecisionAgent
from agents.policy_engine import PolicyResult
from models.claim import ClaimInput
from models.decision import DecisionStatus, LineItemDecision, RejectionReason

agent = DecisionAgent()


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


def _policy_result(
    rejection_reasons=None,
    approved_amount=1350.0,
    fraud_signals=None,
    line_items=None,
) -> PolicyResult:
    pr = PolicyResult()
    pr.rejection_reasons = rejection_reasons or []
    pr.approved_amount = approved_amount
    pr.fraud_signals = fraud_signals or []
    pr.line_items = line_items or []
    return pr


class TestStatusDetermination:
    def test_clean_claim_approved(self):
        result = agent.run(_claim(), _policy_result(), [])
        assert result.status == DecisionStatus.APPROVED

    def test_rejection_reasons_rejected(self):
        pr = _policy_result(rejection_reasons=[RejectionReason.WAITING_PERIOD], approved_amount=0)
        result = agent.run(_claim(), pr, [])
        assert result.status == DecisionStatus.REJECTED

    def test_fraud_signals_manual_review(self):
        pr = _policy_result(fraud_signals=["High-value claim"])
        result = agent.run(_claim(), pr, [])
        assert result.status == DecisionStatus.MANUAL_REVIEW

    def test_partial_line_items_partial(self):
        items = [
            LineItemDecision(description="Root Canal", claimed_amount=8000, approved_amount=8000, status="APPROVED"),
            LineItemDecision(description="Teeth Whitening", claimed_amount=4000, approved_amount=0, status="REJECTED"),
        ]
        pr = _policy_result(line_items=items, approved_amount=8000)
        result = agent.run(_claim(claim_category="DENTAL"), pr, [])
        assert result.status == DecisionStatus.PARTIAL

    def test_all_line_items_rejected_is_rejected(self):
        items = [
            LineItemDecision(description="Teeth Whitening", claimed_amount=4000, approved_amount=0, status="REJECTED"),
        ]
        pr = _policy_result(line_items=items, approved_amount=0)
        result = agent.run(_claim(claim_category="DENTAL"), pr, [])
        assert result.status == DecisionStatus.REJECTED


class TestConfidenceScore:
    def test_clean_pipeline_score_is_1(self):
        result = agent.run(_claim(), _policy_result(), [])
        assert result.confidence_score == 1.0

    def test_one_component_failure_reduces_score(self):
        result = agent.run(_claim(), _policy_result(), ["ExtractionAgent: timeout"])
        assert result.confidence_score == 0.85

    def test_two_component_failures_reduces_score(self):
        result = agent.run(_claim(), _policy_result(), ["AgentA: err", "AgentB: err"])
        assert result.confidence_score == 0.70

    def test_fraud_signal_reduces_score(self):
        pr = _policy_result(fraud_signals=["High-value claim"])
        result = agent.run(_claim(), pr, [])
        assert result.confidence_score == 0.90

    def test_partial_reduces_score(self):
        items = [
            LineItemDecision(description="Root Canal", claimed_amount=8000, approved_amount=8000, status="APPROVED"),
            LineItemDecision(description="Whitening", claimed_amount=4000, approved_amount=0, status="REJECTED"),
        ]
        pr = _policy_result(line_items=items, approved_amount=8000)
        result = agent.run(_claim(claim_category="DENTAL"), pr, [])
        assert result.confidence_score == 0.95


class TestManualReviewRouting:
    def test_fraud_signals_trigger_manual_review(self):
        pr = _policy_result(fraud_signals=["Same-day duplicate"])
        result = agent.run(_claim(), pr, [])
        assert result.manual_review_recommended is True

    def test_component_failure_triggers_manual_review(self):
        result = agent.run(_claim(), _policy_result(), ["ExtractionAgent: failed"])
        assert result.manual_review_recommended is True

    def test_high_value_claim_triggers_manual_review(self):
        result = agent.run(_claim(claimed_amount=30000), _policy_result(approved_amount=30000), [])
        assert result.manual_review_recommended is True

    def test_clean_low_value_no_manual_review(self):
        result = agent.run(_claim(claimed_amount=1500), _policy_result(), [])
        assert result.manual_review_recommended is False


class TestOutputFields:
    def test_approved_amount_echoed(self):
        result = agent.run(_claim(), _policy_result(approved_amount=1350), [])
        assert result.approved_amount == 1350

    def test_member_id_echoed(self):
        result = agent.run(_claim(member_id="EMP005"), _policy_result(), [])
        assert result.member_id == "EMP005"

    def test_claim_id_is_uuid(self):
        import uuid
        result = agent.run(_claim(), _policy_result(), [])
        uuid.UUID(result.claim_id)  # raises if not valid UUID

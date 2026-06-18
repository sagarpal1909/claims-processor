"""
Decision Agent

Takes the PolicyResult and produces the final ClaimDecision.
Computes confidence score based on:
- Completeness of extraction
- Number of component failures
- Fraud signals
- Whether manual review is warranted
"""
from __future__ import annotations
import uuid

from models.claim import ClaimInput
from models.decision import ClaimDecision, DecisionStatus, RejectionReason, TraceStep
from agents.policy_engine import PolicyResult


class DecisionAgent:
    """
    Input : ClaimInput, PolicyResult, component_failures list
    Output: ClaimDecision
    """

    def run(
        self,
        claim: ClaimInput,
        policy_result: PolicyResult,
        component_failures: list[str],
    ) -> ClaimDecision:
        trace: list[TraceStep] = []

        trace.append(TraceStep(
            agent="DecisionAgent",
            step="start",
            status="INFO",
            detail="Computing final claim decision",
        ))

        status, message = self._determine_status(claim, policy_result, component_failures)
        confidence = self._compute_confidence(policy_result, component_failures, status)
        manual_review = self._needs_manual_review(claim, policy_result, component_failures, confidence)

        # Fraud signals warrant a MANUAL_REVIEW status change.
        # Component failures keep the original status but set manual_review_recommended.
        if manual_review and status == DecisionStatus.APPROVED and policy_result.fraud_signals:
            status = DecisionStatus.MANUAL_REVIEW
            message = (
                "Claim routed to manual review due to unusual patterns. "
                + message
            )
        elif manual_review and component_failures and status == DecisionStatus.APPROVED:
            # Keep APPROVED but flag for manual review
            message += " Manual review recommended due to incomplete pipeline processing."

        trace.append(TraceStep(
            agent="DecisionAgent",
            step="decision",
            status="INFO",
            detail=f"Decision: {status} | Confidence: {confidence:.2f} | Manual review: {manual_review}",
            data={
                "status": status,
                "approved_amount": policy_result.approved_amount,
                "confidence": confidence,
                "manual_review": manual_review,
            },
        ))

        if component_failures:
            trace.append(TraceStep(
                agent="DecisionAgent",
                step="component_failures",
                status="WARN",
                detail=f"Pipeline ran with {len(component_failures)} component failure(s): {', '.join(component_failures)}. "
                       "Manual review recommended.",
            ))

        return ClaimDecision(
            claim_id=str(uuid.uuid4()),
            member_id=claim.member_id,
            status=status,
            claimed_amount=claim.claimed_amount,
            approved_amount=policy_result.approved_amount,
            rejection_reasons=policy_result.rejection_reasons,
            message=message,
            line_items=policy_result.line_items,
            confidence_score=confidence,
            trace=policy_result.trace + trace,
            component_failures=component_failures,
            manual_review_recommended=manual_review,
            fraud_signals=policy_result.fraud_signals,
            financial_breakdown=policy_result.financial_breakdown,
        )

    # ------------------------------------------------------------------
    def _determine_status(
        self, claim: ClaimInput, pr: PolicyResult, failures: list[str]
    ) -> tuple[DecisionStatus, str]:
        if pr.rejection_reasons:
            return DecisionStatus.REJECTED, self._rejection_message(pr)

        if pr.fraud_signals:
            return (
                DecisionStatus.MANUAL_REVIEW,
                "Claim flagged for manual review due to unusual activity: "
                + "; ".join(pr.fraud_signals),
            )

        # Partial: some line items rejected, some approved
        if pr.line_items:
            rejected = [li for li in pr.line_items if li.status == "REJECTED"]
            approved = [li for li in pr.line_items if li.status == "APPROVED"]
            if rejected and approved:
                rejected_desc = ", ".join(li.description for li in rejected)
                return (
                    DecisionStatus.PARTIAL,
                    f"Partial approval: {len(rejected)} line item(s) rejected "
                    f"({rejected_desc}) as they are excluded under the policy.",
                )
            if rejected and not approved:
                return DecisionStatus.REJECTED, self._rejection_message(pr)

        return DecisionStatus.APPROVED, (
            f"Claim approved. Approved amount: ₹{pr.approved_amount:,.2f}."
            + (f" {self._financial_summary(pr)}" if pr.financial_breakdown else "")
        )

    def _rejection_message(self, pr: PolicyResult) -> str:
        msgs: list[str] = []
        for step in pr.trace:
            if step.status == "FAIL":
                msgs.append(step.detail)
        return " | ".join(msgs) if msgs else "Claim rejected based on policy rules."

    def _financial_summary(self, pr: PolicyResult) -> str:
        fb = pr.financial_breakdown
        parts: list[str] = []
        if fb.get("network_discount_amount", 0) > 0:
            parts.append(
                f"Network discount ({fb['network_discount_pct']}%) applied: -₹{fb['network_discount_amount']:,.2f}"
            )
        if fb.get("copay_amount", 0) > 0:
            parts.append(
                f"Co-pay ({fb['copay_pct']}%) deducted: -₹{fb['copay_amount']:,.2f}"
            )
        return " | ".join(parts)

    def _compute_confidence(
        self, pr: PolicyResult, failures: list[str], status: DecisionStatus
    ) -> float:
        score = 1.0

        # Each component failure reduces confidence
        score -= len(failures) * 0.15

        # Fraud signals reduce confidence
        score -= len(pr.fraud_signals) * 0.10

        # Partial decisions are slightly less certain
        if status == DecisionStatus.PARTIAL:
            score -= 0.05

        # If there were extraction failures in docs, reduce confidence
        # (tracked via fraud signals proxy — no direct hook needed here)

        return round(max(0.0, min(1.0, score)), 2)

    def _needs_manual_review(
        self,
        claim: ClaimInput,
        pr: PolicyResult,
        failures: list[str],
        confidence: float,
    ) -> bool:
        if pr.fraud_signals:
            return True
        if failures:
            return True
        thresholds = {
            "auto_manual_review_above": 25000,
            "fraud_score_manual_review_threshold": 0.80,
        }
        if claim.claimed_amount >= thresholds["auto_manual_review_above"]:
            return True
        if confidence < (1.0 - thresholds["fraud_score_manual_review_threshold"]):
            return True
        return False

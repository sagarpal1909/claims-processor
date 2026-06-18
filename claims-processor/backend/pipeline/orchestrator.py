"""
Pipeline Orchestrator

Runs agents in sequence. Each agent failure is caught and recorded —
the pipeline never crashes. Component failures reduce confidence and
trigger manual review.

Flow:
  ClaimInput
    → DocumentVerifierAgent   (hard stop on failure — returns error decision)
    → ExtractionAgent         (soft failure — continues with partial data)
    → PolicyEngineAgent       (soft failure — continues with empty result)
    → DecisionAgent           (always runs — produces final decision)
"""
from __future__ import annotations

from agents.decision_agent import DecisionAgent
from agents.document_verifier import DocumentVerificationError, DocumentVerifierAgent
from agents.extractor import ExtractionAgent
from agents.policy_engine import PolicyEngineAgent, PolicyResult
from models.claim import ClaimInput
from models.decision import ClaimDecision, DecisionStatus, RejectionReason, TraceStep
import uuid


class ClaimsPipeline:
    def __init__(self) -> None:
        self.verifier = DocumentVerifierAgent()
        self.extractor = ExtractionAgent()
        self.policy_engine = PolicyEngineAgent()
        self.decision_agent = DecisionAgent()

    def process(self, claim: ClaimInput) -> ClaimDecision:
        component_failures: list[str] = []
        all_trace: list[TraceStep] = []

        # ── Stage 1: Document Verification (hard stop) ──────────────────
        try:
            verify_trace = self.verifier.run(claim)
            all_trace.extend(verify_trace)
        except DocumentVerificationError as e:
            all_trace.extend(e.trace)
            return ClaimDecision(
                claim_id=str(uuid.uuid4()),
                member_id=claim.member_id,
                status=DecisionStatus.REJECTED,
                claimed_amount=claim.claimed_amount,
                approved_amount=0.0,
                rejection_reasons=[e.reason],
                message=str(e),
                confidence_score=1.0,
                trace=all_trace,
                component_failures=[],
                manual_review_recommended=False,
            )
        except Exception as e:
            component_failures.append(f"DocumentVerifier: {e}")
            all_trace.append(TraceStep(
                agent="DocumentVerifier", step="error", status="ERROR",
                detail=f"Document verifier crashed unexpectedly: {e}. Continuing with reduced confidence.",
            ))

        # ── Stage 2: Extraction (soft failure) ───────────────────────────
        extracted: dict = {}
        try:
            if claim.simulate_component_failure:
                raise RuntimeError("Simulated component failure (simulate_component_failure=true)")
            extracted, extract_trace = self.extractor.run(claim)
            all_trace.extend(extract_trace)
        except Exception as e:
            component_failures.append(f"ExtractionAgent: {e}")
            all_trace.append(TraceStep(
                agent="ExtractionAgent", step="error", status="ERROR",
                detail=f"Extraction failed: {e}. Proceeding with available data.",
            ))
            # Fall back to whatever content is already in the documents
            for doc in claim.documents:
                if doc.content:
                    extracted[doc.file_id] = dict(doc.content)

        # ── Stage 3: Policy Engine (soft failure) ────────────────────────
        policy_result = PolicyResult()
        try:
            policy_result = self.policy_engine.run(claim, extracted)
            all_trace.extend([])  # trace already inside policy_result
        except Exception as e:
            component_failures.append(f"PolicyEngine: {e}")
            all_trace.append(TraceStep(
                agent="PolicyEngine", step="error", status="ERROR",
                detail=f"Policy engine failed: {e}. Decision will be based on incomplete evaluation.",
            ))
            policy_result.trace.append(TraceStep(
                agent="PolicyEngine", step="error", status="ERROR",
                detail=str(e),
            ))

        # Merge policy trace into all_trace
        all_trace.extend(policy_result.trace)
        policy_result.trace = []  # avoid duplication in ClaimDecision

        # ── Stage 4: Decision (always runs) ──────────────────────────────
        decision = self.decision_agent.run(claim, policy_result, component_failures)
        decision.trace = all_trace + decision.trace
        return decision

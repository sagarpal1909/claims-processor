from __future__ import annotations
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models.claim import ClaimInput
from models.decision import ClaimDecision
from pipeline.orchestrator import ClaimsPipeline

# Set API key for Claude
if settings.anthropic_api_key:
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

app = FastAPI(title="Claims Processing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = ClaimsPipeline()

# In-memory claim store (replace with a DB in production)
_claims: dict[str, ClaimDecision] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/claims", response_model=ClaimDecision)
def submit_claim(claim: ClaimInput) -> ClaimDecision:
    decision = pipeline.process(claim)
    _claims[decision.claim_id] = decision
    return decision


@app.get("/claims/{claim_id}", response_model=ClaimDecision)
def get_claim(claim_id: str) -> ClaimDecision:
    decision = _claims.get(claim_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Claim not found")
    return decision


@app.get("/claims", response_model=list[ClaimDecision])
def list_claims() -> list[ClaimDecision]:
    return list(_claims.values())


class TestRunResult(BaseModel):
    case_id: str
    case_name: str
    decision: ClaimDecision
    expected_decision: str | None
    expected_amount: float | None
    passed: bool
    notes: str


@app.post("/test-run", response_model=list[TestRunResult])
def run_test_cases() -> list[TestRunResult]:
    test_file = Path(__file__).parent / "tests" / "test_cases.json"
    test_data = json.loads(test_file.read_text())

    results: list[TestRunResult] = []
    for tc in test_data["test_cases"]:
        inp = tc["input"]
        expected = tc.get("expected", {})

        claim = ClaimInput(**inp)
        decision = pipeline.process(claim)
        _claims[decision.claim_id] = decision

        expected_decision = expected.get("decision")
        expected_amount = expected.get("approved_amount")

        passed = True
        notes_parts: list[str] = []

        if expected_decision is not None:
            if decision.status.value != expected_decision:
                passed = False
                notes_parts.append(f"Expected decision '{expected_decision}', got '{decision.status}'")
        else:
            # TC001-003: expect pipeline to stop (no decision)
            if decision.status not in ("REJECTED",):
                notes_parts.append("Expected early stop/rejection, pipeline continued")

        if expected_amount is not None:
            if abs(decision.approved_amount - expected_amount) > 1:
                passed = False
                notes_parts.append(
                    f"Expected amount ₹{expected_amount}, got ₹{decision.approved_amount}"
                )

        results.append(TestRunResult(
            case_id=tc["case_id"],
            case_name=tc["case_name"],
            decision=decision,
            expected_decision=expected_decision,
            expected_amount=expected_amount,
            passed=passed,
            notes=" | ".join(notes_parts) if notes_parts else "OK",
        ))

    return results

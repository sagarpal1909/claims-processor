# Health Insurance Claims Processing System

A multi-agent pipeline that automates health insurance claims adjudication.

## Architecture

```
ClaimInput
  │
  ▼
DocumentVerifierAgent   ← hard stop: wrong type / unreadable / cross-patient mismatch
  │
  ▼
ExtractionAgent         ← Claude vision API (or pre-extracted content in test mode)
  │
  ▼
PolicyEngineAgent       ← waiting periods, exclusions, pre-auth, limits, network discount, co-pay, fraud
  │
  ▼
DecisionAgent           ← APPROVED / PARTIAL / REJECTED / MANUAL_REVIEW + confidence score
  │
  ▼
ClaimDecision (full trace)
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

uvicorn main:app --reload --port 8000
```

### Run test cases (no server needed)

```bash
cd backend
source venv/bin/activate
python -m tests.run_tests
```

### Frontend

```bash
cd frontend
npm install
npm start          # opens http://localhost:3000
```

The React app proxies API calls to `http://localhost:8000`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/claims` | Submit a claim, get a decision |
| GET | `/claims/{id}` | Retrieve a past decision |
| GET | `/claims` | List all decisions |
| POST | `/test-run` | Run all 12 test cases |

## Project Structure

```
backend/
  agents/
    document_verifier.py   # Stage 1 — doc type, readability, cross-patient checks
    extractor.py           # Stage 2 — Claude vision extraction
    policy_engine.py       # Stage 3 — all policy rules
    decision_agent.py      # Stage 4 — final decision + confidence
  pipeline/
    orchestrator.py        # Runs agents, handles soft failures gracefully
  models/
    claim.py               # Input schemas
    decision.py            # Output schemas (ClaimDecision, TraceStep, etc.)
  data/
    policy_terms.json      # Policy configuration (source of truth)
  tests/
    test_cases.json        # 12 test scenarios
    run_tests.py           # Standalone eval runner
  main.py                  # FastAPI app
frontend/
  src/
    components/
      ClaimForm.jsx        # Claim submission UI
      DecisionView.jsx     # Decision + trace viewer
      TestRunner.jsx       # In-browser test runner
    App.jsx
```

## Decision Outcomes

| Status | Meaning |
|--------|---------|
| `APPROVED` | Claim approved, amount calculated after discounts/co-pay |
| `PARTIAL` | Some line items approved, others rejected (e.g. dental exclusions) |
| `REJECTED` | Claim rejected — reason and eligible dates included in message |
| `MANUAL_REVIEW` | Fraud signals or component failures — routed to ops team |

## Confidence Score

Starts at 1.0 and is reduced by:
- Component failures: -0.15 each
- Fraud signals: -0.10 each
- Partial decisions: -0.05

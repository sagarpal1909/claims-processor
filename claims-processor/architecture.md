# Architecture Document — Health Insurance Claims Processing System

## Overview

The system automates OPD health insurance claim adjudication using a sequential multi-agent pipeline. Each agent has a single responsibility, a well-defined input/output contract, and a failure mode that is handled explicitly rather than propagated as an exception.

---

## Pipeline Architecture

```
HTTP POST /claims
        │
        ▼
  ClaimsPipeline.process(ClaimInput)
        │
        ├─► Stage 1: DocumentVerifierAgent  ──── hard stop on failure
        │           ↓ list[TraceStep]
        ├─► Stage 2: ExtractionAgent  ─────────── soft failure, falls back to pre-extracted content
        │           ↓ dict[file_id → extracted_content]
        ├─► Stage 3: PolicyEngineAgent  ────────── soft failure, returns empty PolicyResult
        │           ↓ PolicyResult
        └─► Stage 4: DecisionAgent  ────────────── always runs, produces final decision
                    ↓
            ClaimDecision (HTTP response)
```

### Failure Modes

| Stage | Failure Type | Behaviour |
|---|---|---|
| DocumentVerifier | Hard stop | Returns REJECTED immediately — no further processing |
| ExtractionAgent | Soft failure | Records component failure, falls back to pre-provided `content` field |
| PolicyEngine | Soft failure | Records component failure, continues with empty `PolicyResult` |
| DecisionAgent | Never fails | Wraps all inputs defensively; always returns a `ClaimDecision` |

Soft failures reduce `confidence_score` by 0.15 each and set `manual_review_recommended = true`.

---

## Component Breakdown

### 1. DocumentVerifierAgent

Runs before any document content is read. Performs three checks in order, failing fast on the first error:

1. **Readability** — rejects any document with `quality = UNREADABLE`
2. **Document type** — verifies required document types are present for the claim category
3. **Patient consistency** — cross-checks `patient_name_on_doc` across all uploaded documents

This is the only stage that performs a *hard stop* — it raises `DocumentVerificationError`, which the orchestrator catches and converts directly into a `REJECTED` decision without running downstream agents.

### 2. ExtractionAgent

Extracts structured JSON from uploaded documents using Claude vision (`claude-opus-4-7`).

- **Test mode**: if `DocumentInput.content` is pre-populated, it is passed through unchanged (no API call).
- **Real mode**: sends the base64-encoded document to Claude with a structured extraction prompt. Falls back gracefully if the API call fails.

Output is a `dict[file_id → extracted_content]` consumed by the PolicyEngine.

### 3. PolicyEngineAgent

Applies all policy rules sequentially, accumulating `rejection_reasons` and `trace` steps. Rules are evaluated in this order:

1. Member validation
2. Submission deadline (30 days from treatment)
3. Minimum claim amount (₹500)
4. Initial waiting period (30 days from join date)
5. Specific condition waiting periods (per-condition, 90–730 days)
6. Exclusions (full rejection for excluded treatments)
7. Pre-authorization (for high-value diagnostic tests)
8. Per-claim limit (₹5,000 for non-dental/vision categories)
9. Family floater combined limit (₹1,50,000)
10. Alternative medicine session limit (20/year)
11. Fraud signal detection
12. Financial calculation (sub-limit → network discount → co-pay)

All rules read their thresholds from `data/policy_terms.json` — no hardcoded magic numbers.

### 4. DecisionAgent

Maps `PolicyResult` to a final `ClaimDecision`. Determines:
- **Status**: APPROVED / PARTIAL / REJECTED / MANUAL_REVIEW
- **Confidence score**: starts at 1.0, decremented by component failures (−0.15) and fraud signals (−0.10)
- **Manual review routing**: triggered by fraud signals, component failures, or claims ≥ ₹25,000

---

## Data Flow

```
ClaimInput
├── member_id, policy_id, claim_category, treatment_date
├── claimed_amount, hospital_name
├── ytd_claims_amount  ← family combined YTD for floater check
├── claims_history[]   ← used for same-day fraud detection
└── documents[]
    ├── actual_type, quality, patient_name_on_doc
    ├── content (pre-extracted, test mode)
    └── file_data + file_media_type (base64, real mode)

PolicyResult (internal)
├── rejection_reasons[]
├── line_items[]         ← per-item decisions for DENTAL/VISION
├── approved_amount
├── fraud_signals[]
├── financial_breakdown  ← claimed → sub-limit → network discount → co-pay
└── trace[]

ClaimDecision (API response)
├── status, approved_amount, rejection_reasons[]
├── message             ← human-readable explanation
├── line_items[]
├── confidence_score
├── financial_breakdown
├── fraud_signals[]
├── component_failures[]
├── manual_review_recommended
└── trace[]             ← full per-step audit trail from all agents
```

---

## Design Decisions and Trade-offs

### Sequential pipeline vs. parallel agents

**Chosen:** Sequential, synchronous pipeline.

**Why:** Each stage depends on the output of the previous stage — extraction feeds policy evaluation, which feeds decision. There is no meaningful parallelism in the happy path. A parallel approach would add orchestration complexity (futures, error propagation across concurrent tasks) with no latency benefit.

**Trade-off:** If extraction were split per-document and run concurrently, multi-document claims could be faster. This is a straightforward optimisation if latency becomes a concern.

---

### Hard stop vs. soft failure in DocumentVerifier

**Chosen:** Hard stop — raises an exception that immediately returns `REJECTED`.

**Why:** If documents are wrong or unreadable, all downstream agents (extraction, policy) would produce garbage output. Proceeding wastes API calls and produces a misleading trace. Document failure is a user error, not a system failure.

**Trade-off:** A soft failure here could allow partial processing (e.g., extract the readable documents and flag the rest), but for claims adjudication this creates liability — a decision made on incomplete documents cannot be trusted.

---

### Policy rules in JSON vs. code

**Chosen:** All thresholds and rule parameters live in `data/policy_terms.json`. Rule logic lives in Python.

**Why:** This separates *what* the policy says (data) from *how* to enforce it (code). Insurers change premium structures, waiting periods, and sub-limits every renewal cycle — a JSON edit and restart is far cheaper than a code deployment. Business stakeholders can audit `policy_terms.json` without reading Python.

**Trade-off:** Complex rule interactions (e.g., layered co-pays, condition-specific exclusions) cannot be expressed purely in JSON. The current design keeps a clean split — JSON for thresholds, Python for logic — but a more ambitious version could use a rules-DSL or drools-style rule engine.

---

### Confidence score as a first-class output

**Chosen:** `confidence_score` is always returned, even on `APPROVED` decisions.

**Why:** Downstream consumers (ops dashboards, audit tools) need to distinguish a clean approval from one that passed through a degraded pipeline. A score of 1.0 signals a clean, fully-traced decision. A score of 0.7 with `component_failures` signals the decision is valid but should be spot-checked.

**Trade-off:** The current scoring formula (−0.15 per failure, −0.10 per fraud signal) is heuristic. A calibrated model trained on historical outcomes would be more accurate, but this is proportional and explainable.

---

### Explainability trace on every decision

**Chosen:** Every agent appends `TraceStep` objects to a shared trace. The full trace is returned in the API response.

**Why:** Insurance claim denials have regulatory and legal implications in India (IRDAI mandates written reasons for rejection). The trace also serves as a debugging tool — if a rule fires unexpectedly, the exact policy check that triggered it is visible without log-diving.

**Trade-off:** The trace is verbose (~10–20 steps per claim). For high-volume production use, the trace would be stored in a separate log store (e.g., S3 + Athena) and only returned on request, rather than in every API response.

---

## Scaling to 10× Volume

### Current bottleneck

The primary latency bottleneck is the Claude vision API call in `ExtractionAgent`. Each document makes one synchronous API call (~1–3s). A 3-document claim takes 3–9s end-to-end.

### Path to 10×

| Layer | Current | 10× Approach |
|---|---|---|
| **Extraction** | Synchronous per-document | Async fan-out with `asyncio.gather` — all documents extracted concurrently |
| **API throughput** | One Anthropic API call per doc | Batch requests; cache extraction results by document hash to avoid re-extracting identical uploads |
| **Pipeline** | Synchronous in-process | Move to a task queue (Celery + Redis or AWS SQS) — `POST /claims` enqueues, returns a `claim_id`; client polls `GET /claims/{id}` |
| **Policy engine** | In-memory, single-process | Already stateless and CPU-light — scales horizontally with no changes |
| **Storage** | In-memory dict in `main.py` | Replace with PostgreSQL or DynamoDB; index on `member_id` + `treatment_date` for fraud and limit checks |
| **Family floater** | Caller passes `ytd_claims_amount` | Query a `claims_ledger` table at pipeline start to compute accurate family-combined usage |
| **Rate limits** | None | Add per-member rate limiting at the API gateway layer |

### Async extraction (highest-impact change)

```python
# Current (sequential)
for doc in claim.documents:
    result, steps = self._extract_document(doc)

# 10× (concurrent)
import asyncio
results = await asyncio.gather(*[self._extract_document_async(doc) for doc in claim.documents])
```

This alone reduces extraction latency from O(n_docs) to O(1) (wall-clock = slowest single doc).

### Event-driven alternative

For SLA-sensitive workloads, the pipeline can be split at the extraction boundary:

```
POST /claims  →  validate docs  →  enqueue extraction jobs  →  return 202 Accepted
                                          ↓
                              Worker pool (auto-scales on queue depth)
                                          ↓
                              Policy + Decision  →  store result  →  webhook/push
```

This decouples API response latency from Claude API latency entirely.

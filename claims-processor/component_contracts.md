# Component Contracts

Precise interface definitions for every agent and shared model in the claims pipeline.

---

## Shared Models

### `ClaimInput`
**Module:** `models/claim.py`

| Field | Type | Required | Description |
|---|---|---|---|
| `member_id` | `str` | ✅ | Policy member identifier (e.g. `"EMP001"`) |
| `policy_id` | `str` | ✅ | Policy identifier (e.g. `"PLUM_GHI_2024"`) |
| `claim_category` | `ClaimCategory` | ✅ | One of: `CONSULTATION`, `DIAGNOSTIC`, `PHARMACY`, `DENTAL`, `VISION`, `ALTERNATIVE_MEDICINE` |
| `treatment_date` | `str` | ✅ | ISO 8601 date of treatment (`"YYYY-MM-DD"`) |
| `claimed_amount` | `float` | ✅ | Total amount claimed in INR |
| `hospital_name` | `str \| None` | ❌ | Hospital name — matched against network hospital list for discount |
| `ytd_claims_amount` | `float` | ❌ | Year-to-date claims total for family (default `0.0`). Used for annual OPD limit and family floater checks |
| `claims_history` | `list[ClaimsHistoryEntry]` | ❌ | Prior claims on this policy — used for same-day fraud detection |
| `documents` | `list[DocumentInput]` | ❌ | Uploaded supporting documents |
| `simulate_component_failure` | `bool` | ❌ | Test flag — forces ExtractionAgent to throw (default `false`) |

### `DocumentInput`
**Module:** `models/claim.py`

| Field | Type | Required | Description |
|---|---|---|---|
| `file_id` | `str` | ✅ | Unique identifier for this document within the claim |
| `file_name` | `str` | ❌ | Original filename (used in error messages) |
| `actual_type` | `DocumentType \| None` | ❌ | Declared type — one of: `PRESCRIPTION`, `HOSPITAL_BILL`, `PHARMACY_BILL`, `LAB_REPORT`, `DIAGNOSTIC_REPORT`, `DISCHARGE_SUMMARY`, `DENTAL_REPORT`, `UNKNOWN` |
| `quality` | `DocumentQuality` | ❌ | `GOOD` (default) or `UNREADABLE` — triggers immediate rejection if unreadable |
| `content` | `dict \| None` | ❌ | Pre-extracted content (test mode). If set, ExtractionAgent skips the Claude API call |
| `patient_name_on_doc` | `str \| None` | ❌ | Patient name as it appears on the document — used for cross-patient mismatch check |
| `file_data` | `str \| None` | ❌ | Base64-encoded document bytes (real mode) |
| `file_media_type` | `str \| None` | ❌ | MIME type of `file_data` (e.g. `"image/jpeg"`, `"application/pdf"`) |

### `ClaimDecision`
**Module:** `models/decision.py`

| Field | Type | Description |
|---|---|---|
| `claim_id` | `str` | UUID assigned at decision time |
| `member_id` | `str` | Echoed from `ClaimInput` |
| `status` | `DecisionStatus` | `APPROVED`, `PARTIAL`, `REJECTED`, or `MANUAL_REVIEW` |
| `claimed_amount` | `float` | Echoed from `ClaimInput` |
| `approved_amount` | `float` | Amount approved after all adjustments (0.0 on rejection) |
| `rejection_reasons` | `list[RejectionReason]` | Machine-readable rejection codes |
| `message` | `str` | Human-readable decision explanation |
| `line_items` | `list[LineItemDecision]` | Per-item decisions (populated for DENTAL/VISION partial approvals) |
| `confidence_score` | `float` | 0.0–1.0; 1.0 = clean pipeline, < 1.0 = failures or fraud signals |
| `trace` | `list[TraceStep]` | Full per-step audit trail from all agents |
| `component_failures` | `list[str]` | Names of agents that failed softly |
| `manual_review_recommended` | `bool` | True if a human should inspect this decision |
| `fraud_signals` | `list[str]` | Descriptions of triggered fraud heuristics |
| `financial_breakdown` | `dict \| None` | Step-by-step financial calculation |

### `TraceStep`
**Module:** `models/decision.py`

| Field | Type | Values |
|---|---|---|
| `agent` | `str` | `"DocumentVerifier"`, `"ExtractionAgent"`, `"PolicyEngine"`, `"DecisionAgent"` |
| `step` | `str` | Slug identifying the specific check (e.g. `"submission_deadline"`) |
| `status` | `str` | `"PASS"`, `"FAIL"`, `"WARN"`, `"INFO"`, `"ERROR"` |
| `detail` | `str` | Human-readable explanation of this step's outcome |
| `data` | `dict \| None` | Structured data for this step (thresholds, computed values, etc.) |

---

## Agent Contracts

---

### DocumentVerifierAgent

**Module:** `agents/document_verifier.py`

#### Input
```python
claim: ClaimInput
```

#### Output (success)
```python
list[TraceStep]
# All checks passed. Caller extends the shared trace with these steps.
```

#### Output (failure)
```python
raises DocumentVerificationError
    .reason: RejectionReason   # WRONG_DOCUMENT_TYPE | UNREADABLE_DOCUMENT | CROSS_PATIENT_MISMATCH
    .trace: list[TraceStep]    # Steps up to and including the failing check
```

#### Behaviour contract

1. **Unreadable check** — raises immediately if any `doc.quality == UNREADABLE`. Does not check the remaining documents.
2. **Type check** — raises if required document types for `claim.claim_category` are missing or wrong document types are present. Required types are:

   | Category | Required |
   |---|---|
   | CONSULTATION | PRESCRIPTION, HOSPITAL_BILL |
   | DIAGNOSTIC | PRESCRIPTION, LAB_REPORT, HOSPITAL_BILL |
   | PHARMACY | PRESCRIPTION, PHARMACY_BILL |
   | DENTAL | HOSPITAL_BILL |
   | VISION | PRESCRIPTION, HOSPITAL_BILL |
   | ALTERNATIVE_MEDICINE | PRESCRIPTION, HOSPITAL_BILL |

3. **Patient consistency check** — raises if two or more documents carry different patient names. Documents without a patient name are skipped. If fewer than two documents carry names, this check is skipped (INFO trace step).

#### Invariants
- Checks run in the order above; the first failure raises immediately (no further checks).
- This is the **only** agent that raises an exception to signal failure. All other agents record failures internally.

---

### ExtractionAgent

**Module:** `agents/extractor.py`

#### Input
```python
claim: ClaimInput
```

#### Output
```python
tuple[
    dict[str, dict[str, Any]],  # file_id → extracted_content
    list[TraceStep]
]
```

#### Per-document behaviour

| Condition | Behaviour |
|---|---|
| `doc.content` is set | Pass-through — content returned as-is, no API call |
| `doc.file_data` + `doc.file_media_type` set | Call Claude vision API with base64 image |
| Only `doc.file_name` set (path on disk) | Read file from disk, encode as base64, call Claude |
| No file data available | Call Claude with text-only fallback prompt; returns `{"extraction_failed": true}` |
| Claude API call fails | Returns `{"extraction_failed": true, "error": "<msg>"}`, records ERROR trace step |

#### Extracted content schema (best-effort, fields may be absent)

```json
{
  "document_type": "PRESCRIPTION | HOSPITAL_BILL | ...",
  "patient_name": "string",
  "doctor_name": "string",
  "doctor_registration": "string",
  "hospital_name": "string",
  "date": "YYYY-MM-DD",
  "diagnosis": "string",
  "treatment": "string",
  "medicines": ["string"],
  "tests_ordered": ["string"],
  "line_items": [{"description": "string", "amount": number}],
  "total_amount": number
}
```

#### Failure behaviour
- Exceptions are caught per-document. A single document failure does not abort extraction of other documents.
- The orchestrator falls back to `doc.content` if the API call fails and `doc.content` is set.

---

### PolicyEngineAgent

**Module:** `agents/policy_engine.py`

#### Input
```python
claim: ClaimInput
extracted: dict[str, dict[str, Any]]   # output of ExtractionAgent
```

#### Output
```python
PolicyResult
```

**`PolicyResult` fields:**

| Field | Type | Description |
|---|---|---|
| `rejection_reasons` | `list[RejectionReason]` | All triggered rejection codes. Empty = no rejection. |
| `line_items` | `list[LineItemDecision]` | Per-item decisions (DENTAL only) |
| `approved_amount` | `float` | Computed eligible amount (0.0 if rejections exist) |
| `network_discount_applied` | `float` | Discount amount applied (₹) |
| `copay_deducted` | `float` | Co-pay amount deducted (₹) |
| `fraud_signals` | `list[str]` | Descriptions of triggered fraud heuristics |
| `trace` | `list[TraceStep]` | Per-rule audit steps |
| `financial_breakdown` | `dict` | Step-by-step financial calculation |

#### Rule evaluation order

Rules are evaluated sequentially. All are evaluated unless the first rule (member validation) fails — in that case, evaluation stops immediately and returns.

| Step | Method | Rejection Code on Failure |
|---|---|---|
| Member validation | `_validate_member` | `MEMBER_NOT_FOUND` — **hard stop** |
| Submission deadline | `_check_submission_deadline` | `WAITING_PERIOD` |
| Minimum amount | `_check_minimum_claim_amount` | `PER_CLAIM_EXCEEDED` |
| Initial waiting period | `_check_initial_waiting_period` | `WAITING_PERIOD` |
| Condition waiting periods | `_check_specific_waiting_periods` | `WAITING_PERIOD` |
| Exclusions | `_check_exclusions` | `EXCLUDED_CONDITION` |
| Pre-authorization | `_check_pre_authorization` | `PRE_AUTH_MISSING` |
| Per-claim limit | `_check_per_claim_limit` | `PER_CLAIM_EXCEEDED` |
| Family floater limit | `_check_family_floater_limit` | `ANNUAL_LIMIT_EXCEEDED` |
| Alt medicine sessions | `_check_alt_medicine_sessions` | `SUB_LIMIT_EXCEEDED` |
| Fraud detection | `_check_fraud_signals` | — (populates `fraud_signals`, no rejection) |
| Financial calculation | `_calculate_approved_amount` | — (only runs if no rejections) |

#### Financial calculation contract

Applied in this order, each reducing the base eligible amount:
1. Dental line-item filtering (rejected items removed from base)
2. Annual OPD limit check — caps base at remaining OPD headroom
3. Network discount — applied if `hospital_name` matches a network hospital
4. Pharmacy branded co-pay — applied if `PHARMACY` claim and no generic mention detected
5. Category co-pay — applied as configured per category

**Formula:** `approved = (base - network_discount) × (1 - copay_pct/100)`

#### Key heuristics
- Condition detection uses keyword matching on combined extracted text (`CONDITION_KEYWORDS` dict).
- Exclusion detection uses keyword matching on combined extracted text (`EXCLUSION_KEYWORDS` list).
- Network hospital matching is case-insensitive substring match in either direction.

---

### DecisionAgent

**Module:** `agents/decision_agent.py`

#### Input
```python
claim: ClaimInput
policy_result: PolicyResult
component_failures: list[str]
```

#### Output
```python
ClaimDecision
```

#### Status determination

| Condition | Status |
|---|---|
| `policy_result.rejection_reasons` non-empty | `REJECTED` |
| `policy_result.fraud_signals` non-empty | `MANUAL_REVIEW` |
| `line_items` has both APPROVED and REJECTED items | `PARTIAL` |
| All line items rejected, none approved | `REJECTED` |
| Otherwise | `APPROVED` |

**Override:** If status is `APPROVED` but `fraud_signals` are present, status becomes `MANUAL_REVIEW`.

#### Confidence score formula

```
score = 1.0
score -= len(component_failures) × 0.15
score -= len(fraud_signals) × 0.10
score -= 0.05  (if status == PARTIAL)
score = clamp(score, 0.0, 1.0)
```

#### Manual review routing

`manual_review_recommended = true` if any of:
- `fraud_signals` non-empty
- `component_failures` non-empty
- `claimed_amount >= 25,000`
- `confidence_score < 0.20`

---

## Orchestrator Contract

**Module:** `pipeline/orchestrator.py`

#### Input
```python
claim: ClaimInput
```

#### Output
```python
ClaimDecision
```

#### Guarantees
- Always returns a `ClaimDecision` — never raises an exception to the caller.
- `DocumentVerificationError` is caught and converted to a `REJECTED` decision.
- All other agent exceptions are caught, recorded in `component_failures`, and the pipeline continues.
- The final `ClaimDecision.trace` contains the concatenated trace steps from all agents in pipeline order.

---

## Rejection Reason Reference

| Code | Meaning |
|---|---|
| `WAITING_PERIOD` | Treatment date falls within a waiting period, or submission was too late |
| `PRE_AUTH_MISSING` | High-value diagnostic test without pre-authorization |
| `PER_CLAIM_EXCEEDED` | Claimed amount exceeds per-claim limit, or below minimum claim amount |
| `SUB_LIMIT_EXCEEDED` | Category sub-limit or session limit exhausted |
| `ANNUAL_LIMIT_EXCEEDED` | Annual OPD or family floater combined limit exceeded |
| `EXCLUDED_CONDITION` | Claim contains a policy-excluded treatment |
| `WRONG_DOCUMENT_TYPE` | Incorrect or missing document type for claim category |
| `UNREADABLE_DOCUMENT` | Uploaded document is too blurry or damaged to process |
| `CROSS_PATIENT_MISMATCH` | Documents belong to different patients |
| `FRAUD_SIGNAL` | Unusual claim pattern detected (not currently used as rejection; routed to MANUAL_REVIEW) |
| `MEMBER_NOT_FOUND` | `member_id` not in policy roster |
| `POLICY_INACTIVE` | Policy period has expired (reserved for future use) |

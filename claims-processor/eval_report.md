# Claims Processing System — Eval Report

**Generated:** 2026-06-17 15:48:56  
**Test cases:** 12  
**Result:** 12/12 passed

---

## Summary

| Case | Name | Decision | Approved (₹) | Confidence | Result |
|------|------|----------|--------------|------------|--------|
| TC001 | Wrong Document Uploaded | REJECTED | ₹0.00 | 100% | ✅ |
| TC002 | Unreadable Document | REJECTED | ₹0.00 | 100% | ✅ |
| TC003 | Documents Belong to Different Patients | REJECTED | ₹0.00 | 100% | ✅ |
| TC004 | Clean Consultation — Full Approval | APPROVED | ₹1,350.00 | 100% | ✅ |
| TC005 | Waiting Period — Diabetes | REJECTED | ₹0.00 | 100% | ✅ |
| TC006 | Dental Partial Approval — Cosmetic Exclusion | PARTIAL | ₹8,000.00 | 95% | ✅ |
| TC007 | MRI Without Pre-Authorization | REJECTED | ₹0.00 | 100% | ✅ |
| TC008 | Per-Claim Limit Exceeded | REJECTED | ₹0.00 | 100% | ✅ |
| TC009 | Fraud Signal — Multiple Same-Day Claims | MANUAL_REVIEW | ₹4,320.00 | 90% | ✅ |
| TC010 | Network Hospital — Discount Applied | APPROVED | ₹3,240.00 | 100% | ✅ |
| TC011 | Component Failure — Graceful Degradation | APPROVED | ₹4,000.00 | 85% | ✅ |
| TC012 | Excluded Treatment | REJECTED | ₹0.00 | 100% | ✅ |

---

## TC001: Wrong Document Uploaded

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED/STOPPED`  

**Message:** Your ClaimCategory.CONSULTATION claim is missing required document(s): HOSPITAL_BILL. You uploaded: PRESCRIPTION, PRESCRIPTION. Please provide the missing document(s) and resubmit.

**Rejection Reasons:**

- `WRONG_DOCUMENT_TYPE`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
❌ **DocumentVerifier** › `type_check`  
   Your ClaimCategory.CONSULTATION claim is missing required document(s): HOSPITAL_BILL. You uploaded: PRESCRIPTION, PRESCRIPTION. Please provide the missing document(s) and resubmit.  

---

## TC002: Unreadable Document

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED/STOPPED`  

**Message:** The document 'blurry_bill.jpg' (type: DocumentType.PHARMACY_BILL) could not be read — the image is too blurry or damaged. Please re-upload a clear, well-lit photo of this document.

**Rejection Reasons:**

- `UNREADABLE_DOCUMENT`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.PHARMACY claim  
❌ **DocumentVerifier** › `readability_check`  
   The document 'blurry_bill.jpg' (type: DocumentType.PHARMACY_BILL) could not be read — the image is too blurry or damaged. Please re-upload a clear, well-lit photo of this document.  

---

## TC003: Documents Belong to Different Patients

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED/STOPPED`  

**Message:** The documents you uploaded appear to belong to different patients. Patient names found: F005 → 'Rajesh Kumar', F006 → 'Arjun Mehta'. Please ensure all documents are for the same patient and resubmit.

**Rejection Reasons:**

- `CROSS_PATIENT_MISMATCH`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
❌ **DocumentVerifier** › `patient_consistency_check`  
   The documents you uploaded appear to belong to different patients. Patient names found: F005 → 'Rajesh Kumar', F006 → 'Arjun Mehta'. Please ensure all documents are for the same patient and resubmit.  

---

## TC004: Clean Consultation — Full Approval

**Result:** ✅ PASS  
**Decision:** `APPROVED`  
**Approved Amount:** ₹1,350.00  
**Confidence Score:** 100%  
**Expected Decision:** `APPROVED`  
**Expected Amount:** ₹1,350.00  

**Message:** Claim approved. Approved amount: ₹1,350.00. Co-pay (10%) deducted: -₹150.00

**Financial Breakdown:**

- Claimed Amount: ₹1,500.00
- Base Eligible: ₹1,500.00
- Network Discount Pct: 0
- Network Discount Amount: ₹0.00
- Copay Pct: 10
- Copay Amount: ₹150.00
- Approved Amount: ₹1,350.00

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
✅ **DocumentVerifier** › `patient_consistency_check`  
   Patient name consistent across all documents: 'Rajesh Kumar'  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F007`  
   Used pre-provided content for F007 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F008`  
   Used pre-provided content for F008 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Rajesh Kumar (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹1,500.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
✅ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹1,500.0 is within per-claim limit ₹5,000  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹6,500 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
✅ **PolicyEngine** › `sub_limit_check`  
   Within annual OPD limit of ₹50,000  
ℹ️ **PolicyEngine** › `copay`  
   Co-pay 10% applied: -₹150.00  
✅ **PolicyEngine** › `financial_calculation`  
   Approved amount: ₹1,350.00  
✅ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: none  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.APPROVED | Confidence: 1.00 | Manual review: False  

---

## TC005: Waiting Period — Diabetes

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED`  

**Message:** Claim rejected based on policy rules.

**Rejection Reasons:**

- `WAITING_PERIOD`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
✅ **DocumentVerifier** › `patient_consistency_check`  
   Patient name consistent across all documents: 'Vikram Joshi'  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F009`  
   Used pre-provided content for F009 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F010`  
   Used pre-provided content for F010 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Vikram Joshi (joined 2024-09-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹3,000.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-10-01)  
❌ **PolicyEngine** › `waiting_period_diabetes`  
   Condition 'diabetes' has a 90-day waiting period. Treatment on 2024-10-15 is before eligibility date 2024-11-30. This claim will be eligible from 2024-11-30.  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
✅ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹3,000.0 is within per-claim limit ₹5,000  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹3,000 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
❌ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: [<RejectionReason.WAITING_PERIOD: 'WAITING_PERIOD'>]  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.REJECTED | Confidence: 1.00 | Manual review: False  

---

## TC006: Dental Partial Approval — Cosmetic Exclusion

**Result:** ✅ PASS  
**Decision:** `PARTIAL`  
**Approved Amount:** ₹8,000.00  
**Confidence Score:** 95%  
**Expected Decision:** `PARTIAL`  
**Expected Amount:** ₹8,000.00  

**Message:** Partial approval: 1 line item(s) rejected (Teeth Whitening) as they are excluded under the policy.

**Financial Breakdown:**

- Claimed Amount: ₹12,000.00
- Base Eligible: 10000
- Network Discount Pct: 0
- Network Discount Amount: ₹0.00
- Copay Pct: 0
- Copay Amount: ₹0.00
- Approved Amount: ₹8,000.00

**Line Item Decisions:**

| Item | Claimed | Approved | Status | Reason |
|------|---------|----------|--------|--------|
| Root Canal Treatment | ₹8,000 | ₹8,000 | APPROVED | — |
| Teeth Whitening | ₹4,000 | ₹0 | REJECTED | Cosmetic/excluded dental procedure not covered under policy |

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 1 document(s) for ClaimCategory.DENTAL claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 1 document(s)  
✅ **ExtractionAgent** › `extract_F011`  
   Used pre-provided content for F011 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 1 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Priya Singh (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹12,000.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
ℹ️ **PolicyEngine** › `per_claim_limit`  
   Per-claim limit check skipped for ClaimCategory.DENTAL — governed by category sub-limit  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹12,000 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
✅ **PolicyEngine** › `sub_limit_check`  
   Within annual OPD limit of ₹50,000  
✅ **PolicyEngine** › `financial_calculation`  
   Approved amount: ₹8,000.00  
✅ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: none  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.PARTIAL | Confidence: 0.95 | Manual review: False  

---

## TC007: MRI Without Pre-Authorization

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED`  

**Message:** Claim rejected based on policy rules.

**Rejection Reasons:**

- `WAITING_PERIOD`
- `PRE_AUTH_MISSING`
- `PER_CLAIM_EXCEEDED`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 3 document(s) for ClaimCategory.DIAGNOSTIC claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'LAB_REPORT', 'HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 3 document(s)  
✅ **ExtractionAgent** › `extract_F012`  
   Used pre-provided content for F012 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F013`  
   Used pre-provided content for F013 (DocumentType.LAB_REPORT)  
✅ **ExtractionAgent** › `extract_F014`  
   Used pre-provided content for F014 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 3 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Suresh Patil (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹15,000.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
❌ **PolicyEngine** › `waiting_period_hernia`  
   Condition 'hernia' has a 365-day waiting period. Treatment on 2024-11-02 is before eligibility date 2025-04-01. This claim will be eligible from 2025-04-01.  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
❌ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization is required for MRI when the amount exceeds ₹10,000. Claimed amount ₹15,000.0 exceeds this threshold but no pre-auth was provided. To resubmit: obtain pre-authorization from the insurer before the procedure and attach the approval number.  
❌ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹15,000.0 exceeds the per-claim limit of ₹5,000. Only claims up to this limit are eligible for reimbursement.  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹15,000 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
❌ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: [<RejectionReason.WAITING_PERIOD: 'WAITING_PERIOD'>, <RejectionReason.PRE_AUTH_MISSING: 'PRE_AUTH_MISSING'>, <RejectionReason.PER_CLAIM_EXCEEDED: 'PER_CLAIM_EXCEEDED'>]  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.REJECTED | Confidence: 1.00 | Manual review: False  

---

## TC008: Per-Claim Limit Exceeded

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED`  

**Message:** Claim rejected based on policy rules.

**Rejection Reasons:**

- `PER_CLAIM_EXCEEDED`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F015`  
   Used pre-provided content for F015 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F016`  
   Used pre-provided content for F016 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Amit Verma (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹7,500.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
❌ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹7,500.0 exceeds the per-claim limit of ₹5,000. Only claims up to this limit are eligible for reimbursement.  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹17,500 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
❌ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: [<RejectionReason.PER_CLAIM_EXCEEDED: 'PER_CLAIM_EXCEEDED'>]  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.REJECTED | Confidence: 1.00 | Manual review: False  

---

## TC009: Fraud Signal — Multiple Same-Day Claims

**Result:** ✅ PASS  
**Decision:** `MANUAL_REVIEW`  
**Approved Amount:** ₹4,320.00  
**Confidence Score:** 90%  
**Expected Decision:** `MANUAL_REVIEW`  

**Message:** Claim flagged for manual review due to unusual activity: 3 prior claims already submitted on 2024-10-30 (limit: 2)

**Fraud Signals:**

- 3 prior claims already submitted on 2024-10-30 (limit: 2)

**Financial Breakdown:**

- Claimed Amount: ₹4,800.00
- Base Eligible: 2000
- Network Discount Pct: 0
- Network Discount Amount: ₹0.00
- Copay Pct: 10
- Copay Amount: ₹480.00
- Approved Amount: ₹4,320.00

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F017`  
   Used pre-provided content for F017 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F018`  
   Used pre-provided content for F018 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Ravi Menon (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹4,800.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
✅ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹4,800.0 is within per-claim limit ₹5,000  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹4,800 projected of ₹150,000 combined limit  
⚠️ **PolicyEngine** › `fraud_check`  
   Fraud signals detected: 3 prior claims already submitted on 2024-10-30 (limit: 2)  
✅ **PolicyEngine** › `sub_limit_check`  
   Within annual OPD limit of ₹50,000  
ℹ️ **PolicyEngine** › `copay`  
   Co-pay 10% applied: -₹480.00  
✅ **PolicyEngine** › `financial_calculation`  
   Approved amount: ₹4,320.00  
✅ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: none  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.MANUAL_REVIEW | Confidence: 0.90 | Manual review: True  

---

## TC010: Network Hospital — Discount Applied

**Result:** ✅ PASS  
**Decision:** `APPROVED`  
**Approved Amount:** ₹3,240.00  
**Confidence Score:** 100%  
**Expected Decision:** `APPROVED`  
**Expected Amount:** ₹3,240.00  

**Message:** Claim approved. Approved amount: ₹3,240.00. Network discount (20%) applied: -₹900.00 | Co-pay (10%) deducted: -₹360.00

**Financial Breakdown:**

- Claimed Amount: ₹4,500.00
- Base Eligible: 2000
- Network Discount Pct: 20
- Network Discount Amount: ₹900.00
- Copay Pct: 10
- Copay Amount: ₹360.00
- Approved Amount: ₹3,240.00

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
✅ **DocumentVerifier** › `patient_consistency_check`  
   Patient name consistent across all documents: 'Deepak Shah'  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F019`  
   Used pre-provided content for F019 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F020`  
   Used pre-provided content for F020 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Deepak Shah (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹4,500.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
✅ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹4,500.0 is within per-claim limit ₹5,000  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹12,500 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
✅ **PolicyEngine** › `sub_limit_check`  
   Within annual OPD limit of ₹50,000  
ℹ️ **PolicyEngine** › `network_discount`  
   Network hospital discount 20% applied: -₹900.00  
ℹ️ **PolicyEngine** › `copay`  
   Co-pay 10% applied: -₹360.00  
✅ **PolicyEngine** › `financial_calculation`  
   Approved amount: ₹3,240.00  
✅ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: none  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.APPROVED | Confidence: 1.00 | Manual review: False  

---

## TC011: Component Failure — Graceful Degradation

**Result:** ✅ PASS  
**Decision:** `APPROVED`  
**Approved Amount:** ₹4,000.00  
**Confidence Score:** 85%  
**Expected Decision:** `APPROVED`  

**Message:** Claim approved. Approved amount: ₹4,000.00.  Manual review recommended due to incomplete pipeline processing.

**Component Failures:**

- ExtractionAgent: Simulated component failure (simulate_component_failure=true)

**Financial Breakdown:**

- Claimed Amount: ₹4,000.00
- Base Eligible: ₹4,000.00
- Network Discount Pct: 0
- Network Discount Amount: ₹0.00
- Copay Pct: 0
- Copay Amount: ₹0.00
- Approved Amount: ₹4,000.00

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.ALTERNATIVE_MEDICINE claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
🔴 **ExtractionAgent** › `error`  
   Extraction failed: Simulated component failure (simulate_component_failure=true). Proceeding with available data.  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Kavita Nair (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹4,000.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
✅ **PolicyEngine** › `specific_waiting_periods`  
   No specific condition waiting period applies  
✅ **PolicyEngine** › `exclusion_check`  
   No policy exclusions triggered  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
✅ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹4,000.0 is within per-claim limit ₹5,000  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹4,000 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `alt_medicine_sessions`  
   Alternative medicine sessions: 0/20 used this year  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
✅ **PolicyEngine** › `sub_limit_check`  
   Within annual OPD limit of ₹50,000  
✅ **PolicyEngine** › `financial_calculation`  
   Approved amount: ₹4,000.00  
✅ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: none  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.APPROVED | Confidence: 0.85 | Manual review: True  
⚠️ **DecisionAgent** › `component_failures`  
   Pipeline ran with 1 component failure(s): ExtractionAgent: Simulated component failure (simulate_component_failure=true). Manual review recommended.  

---

## TC012: Excluded Treatment

**Result:** ✅ PASS  
**Decision:** `REJECTED`  
**Approved Amount:** ₹0.00  
**Confidence Score:** 100%  
**Expected Decision:** `REJECTED`  

**Message:** Claim rejected based on policy rules.

**Rejection Reasons:**

- `WAITING_PERIOD`
- `EXCLUDED_CONDITION`
- `PER_CLAIM_EXCEEDED`

**Full Decision Trace:**

ℹ️ **DocumentVerifier** › `start`  
   Verifying 2 document(s) for ClaimCategory.CONSULTATION claim  
✅ **DocumentVerifier** › `readability_check`  
   All documents are readable  
✅ **DocumentVerifier** › `type_check`  
   All required document types present: ['PRESCRIPTION', 'HOSPITAL_BILL']  
ℹ️ **DocumentVerifier** › `patient_consistency_check`  
   Not enough named documents to cross-check patient identity  
✅ **DocumentVerifier** › `complete`  
   All document checks passed  
ℹ️ **ExtractionAgent** › `start`  
   Extracting data from 2 document(s)  
✅ **ExtractionAgent** › `extract_F023`  
   Used pre-provided content for F023 (DocumentType.PRESCRIPTION)  
✅ **ExtractionAgent** › `extract_F024`  
   Used pre-provided content for F024 (DocumentType.HOSPITAL_BILL)  
✅ **ExtractionAgent** › `complete`  
   Extraction complete for 2 document(s)  
ℹ️ **PolicyEngine** › `start`  
   Starting policy evaluation  
✅ **PolicyEngine** › `member_validation`  
   Member found: Anita Desai (joined 2024-04-01)  
✅ **PolicyEngine** › `submission_deadline`  
   Submitted within deadline: 7 days after treatment (limit: 30 days)  
✅ **PolicyEngine** › `minimum_claim_amount`  
   Claimed amount ₹8,000.0 meets minimum ₹500  
✅ **PolicyEngine** › `initial_waiting_period`  
   Initial waiting period satisfied (eligible from 2024-05-01)  
❌ **PolicyEngine** › `waiting_period_obesity_treatment`  
   Condition 'obesity_treatment' has a 365-day waiting period. Treatment on 2024-10-18 is before eligibility date 2025-04-01. This claim will be eligible from 2025-04-01.  
❌ **PolicyEngine** › `exclusion_check`  
   Claim contains excluded treatment(s): bariatric, obesity. These are not covered under the policy.  
ℹ️ **PolicyEngine** › `pre_auth_check`  
   Pre-authorization check not applicable for this claim category  
❌ **PolicyEngine** › `per_claim_limit`  
   Claimed amount ₹8,000.0 exceeds the per-claim limit of ₹5,000. Only claims up to this limit are eligible for reimbursement.  
✅ **PolicyEngine** › `family_floater_limit`  
   Family floater limit OK: ₹8,000 projected of ₹150,000 combined limit  
✅ **PolicyEngine** › `fraud_check`  
   No fraud signals detected  
❌ **PolicyEngine** › `complete`  
   Policy evaluation complete. Rejections: [<RejectionReason.WAITING_PERIOD: 'WAITING_PERIOD'>, <RejectionReason.EXCLUDED_CONDITION: 'EXCLUDED_CONDITION'>, <RejectionReason.PER_CLAIM_EXCEEDED: 'PER_CLAIM_EXCEEDED'>]  
ℹ️ **DecisionAgent** › `start`  
   Computing final claim decision  
ℹ️ **DecisionAgent** › `decision`  
   Decision: DecisionStatus.REJECTED | Confidence: 1.00 | Manual review: False  

---

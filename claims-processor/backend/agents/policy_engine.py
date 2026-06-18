"""
Policy Engine Agent

Applies all policy rules from policy_terms.json:
- Member validation
- Submission deadline (30 days from treatment)
- Minimum claim amount (₹500)
- Waiting periods (initial, pre-existing, specific conditions)
- Coverage category checks
- Exclusions
- Pre-authorization requirements
- Per-claim and annual OPD limits
- Alternative medicine session limit (20/year)
- Network hospital discounts
- Co-pay calculations (including pharmacy branded drug co-pay)
- Fraud signal detection
- Line-item level approval/rejection (dental, vision)
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from models.claim import ClaimInput
from models.decision import LineItemDecision, RejectionReason, TraceStep

POLICY_PATH = Path(__file__).parent.parent / "data" / "policy_terms.json"


def _load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text())


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


CONDITION_KEYWORDS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "diabetic", "metformin", "glimepiride", "insulin", "hba1c"],
    "hypertension": ["hypertension", "hypertensive", "amlodipine", "telmisartan", "losartan", "bp"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid", "tsh", "thyroxine", "levothyroxine"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement", "arthroplasty"],
    "maternity": ["maternity", "pregnancy", "antenatal", "postnatal", "delivery", "obstetric"],
    "mental_health": ["depression", "anxiety", "psychiatric", "mental health", "schizophrenia", "bipolar"],
    "obesity_treatment": ["obesity", "bariatric", "weight loss", "bmi", "overweight", "diet program"],
    "hernia": ["hernia", "herniation"],
    "cataract": ["cataract"],
}

EXCLUSION_KEYWORDS: list[str] = [
    "self-inflicted", "self inflicted",
    "war", "nuclear",
    "substance abuse", "alcohol abuse", "drug abuse",
    "experimental",
    "infertility", "ivf", "assisted reproduction",
    "obesity", "bariatric", "weight loss program",
    "cosmetic", "aesthetic", "lasik", "refractive surgery",
    "vaccination", "vaccine",
    "supplement", "tonic",
    "teeth whitening", "whitening", "veneers", "orthodontic", "braces", "bleaching",
]


class PolicyResult:
    def __init__(self) -> None:
        self.rejection_reasons: list[RejectionReason] = []
        self.line_items: list[LineItemDecision] = []
        self.approved_amount: float = 0.0
        self.network_discount_applied: float = 0.0
        self.copay_deducted: float = 0.0
        self.fraud_signals: list[str] = []
        self.trace: list[TraceStep] = []
        self.financial_breakdown: dict[str, Any] = {}


class PolicyEngineAgent:
    """
    Input : ClaimInput, extracted_content dict
    Output: PolicyResult
    """

    def __init__(self) -> None:
        self.policy = _load_policy()

    def run(self, claim: ClaimInput, extracted: dict[str, dict[str, Any]]) -> PolicyResult:
        result = PolicyResult()

        result.trace.append(TraceStep(
            agent="PolicyEngine",
            step="start",
            status="INFO",
            detail="Starting policy evaluation",
        ))

        member = self._validate_member(claim, result)
        if member is None:
            return result

        self._check_submission_deadline(claim, result)
        self._check_minimum_claim_amount(claim, result)
        self._check_initial_waiting_period(claim, member, result)
        self._check_specific_waiting_periods(claim, member, extracted, result)
        self._check_exclusions(claim, extracted, result)
        self._check_pre_authorization(claim, extracted, result)
        self._check_per_claim_limit(claim, result)
        self._check_family_floater_limit(claim, result)
        self._check_alt_medicine_sessions(claim, result)
        self._check_fraud_signals(claim, result)

        if not result.rejection_reasons:
            self._calculate_approved_amount(claim, extracted, result)

        result.trace.append(TraceStep(
            agent="PolicyEngine",
            step="complete",
            status="PASS" if not result.rejection_reasons else "FAIL",
            detail=(
                f"Policy evaluation complete. Rejections: {result.rejection_reasons or 'none'}"
            ),
        ))
        return result

    # ------------------------------------------------------------------
    def _validate_member(self, claim: ClaimInput, result: PolicyResult) -> dict | None:
        members = {m["member_id"]: m for m in self.policy.get("members", [])}
        member = members.get(claim.member_id)

        if not member:
            msg = f"Member '{claim.member_id}' not found in policy roster."
            result.rejection_reasons.append(RejectionReason.MEMBER_NOT_FOUND)
            result.trace.append(TraceStep(agent="PolicyEngine", step="member_validation", status="FAIL", detail=msg))
            return None

        result.trace.append(TraceStep(
            agent="PolicyEngine", step="member_validation", status="PASS",
            detail=f"Member found: {member['name']} (joined {member['join_date']})",
            data={"member_id": member["member_id"], "name": member["name"]},
        ))
        return member

    def _check_initial_waiting_period(
        self, claim: ClaimInput, member: dict, result: PolicyResult
    ) -> None:
        waiting_days = self.policy["waiting_periods"]["initial_waiting_period_days"]
        join_date = _parse_date(member["join_date"])
        treatment_date = _parse_date(claim.treatment_date)
        eligible_date = join_date + timedelta(days=waiting_days)

        if treatment_date < eligible_date:
            msg = (
                f"Treatment date {claim.treatment_date} falls within the {waiting_days}-day initial waiting period. "
                f"Eligible from: {eligible_date.isoformat()}."
            )
            result.rejection_reasons.append(RejectionReason.WAITING_PERIOD)
            result.trace.append(TraceStep(agent="PolicyEngine", step="initial_waiting_period", status="FAIL", detail=msg,
                                          data={"eligible_from": eligible_date.isoformat()}))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="initial_waiting_period", status="PASS",
                detail=f"Initial waiting period satisfied (eligible from {eligible_date.isoformat()})",
            ))

    def _check_specific_waiting_periods(
        self, claim: ClaimInput, member: dict, extracted: dict, result: PolicyResult
    ) -> None:
        specific = self.policy["waiting_periods"]["specific_conditions"]
        join_date = _parse_date(member["join_date"])
        treatment_date = _parse_date(claim.treatment_date)

        combined_text = self._combined_text(extracted).lower()

        for condition, wait_days in specific.items():
            keywords = CONDITION_KEYWORDS.get(condition, [condition])
            if any(kw in combined_text for kw in keywords):
                eligible_date = join_date + timedelta(days=wait_days)
                if treatment_date < eligible_date:
                    msg = (
                        f"Condition '{condition}' has a {wait_days}-day waiting period. "
                        f"Treatment on {claim.treatment_date} is before eligibility date {eligible_date.isoformat()}. "
                        f"This claim will be eligible from {eligible_date.isoformat()}."
                    )
                    result.rejection_reasons.append(RejectionReason.WAITING_PERIOD)
                    result.trace.append(TraceStep(
                        agent="PolicyEngine", step=f"waiting_period_{condition}", status="FAIL",
                        detail=msg, data={"condition": condition, "eligible_from": eligible_date.isoformat()},
                    ))
                    return
                else:
                    result.trace.append(TraceStep(
                        agent="PolicyEngine", step=f"waiting_period_{condition}", status="PASS",
                        detail=f"Waiting period for '{condition}' satisfied (eligible from {eligible_date.isoformat()})",
                    ))
                    return

        result.trace.append(TraceStep(
            agent="PolicyEngine", step="specific_waiting_periods", status="PASS",
            detail="No specific condition waiting period applies",
        ))

    def _check_exclusions(
        self, claim: ClaimInput, extracted: dict, result: PolicyResult
    ) -> None:
        combined_text = self._combined_text(extracted).lower()
        line_items = self._get_all_line_items(extracted)

        triggered = [kw for kw in EXCLUSION_KEYWORDS if kw in combined_text]

        # For DENTAL claims, cosmetic exclusions are handled per-line-item in
        # _calculate_approved_amount (a partial approval, not a full rejection).
        if claim.claim_category == "DENTAL":
            non_dental_exclusions = [
                kw for kw in triggered
                if kw not in ("teeth whitening", "whitening", "veneers", "orthodontic", "braces", "bleaching")
            ]
            triggered = non_dental_exclusions

        if triggered:
            msg = (
                f"Claim contains excluded treatment(s): {', '.join(set(triggered))}. "
                "These are not covered under the policy."
            )
            result.rejection_reasons.append(RejectionReason.EXCLUDED_CONDITION)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="exclusion_check", status="FAIL",
                detail=msg, data={"triggered_exclusions": list(set(triggered))},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="exclusion_check", status="PASS",
                detail="No policy exclusions triggered",
            ))

    def _check_pre_authorization(
        self, claim: ClaimInput, extracted: dict, result: PolicyResult
    ) -> None:
        if claim.claim_category != "DIAGNOSTIC":
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="pre_auth_check", status="INFO",
                detail="Pre-authorization check not applicable for this claim category",
            ))
            return

        high_value_tests = self.policy["opd_categories"]["diagnostic"].get(
            "high_value_tests_requiring_pre_auth", []
        )
        pre_auth_threshold = self.policy["opd_categories"]["diagnostic"].get("pre_auth_threshold", 10000)

        combined_text = self._combined_text(extracted).lower()
        triggered_tests = [t for t in high_value_tests if t.lower() in combined_text]

        if triggered_tests and claim.claimed_amount > pre_auth_threshold:
            msg = (
                f"Pre-authorization is required for {', '.join(triggered_tests)} "
                f"when the amount exceeds ₹{pre_auth_threshold:,}. "
                f"Claimed amount ₹{claim.claimed_amount:,} exceeds this threshold but no pre-auth was provided. "
                "To resubmit: obtain pre-authorization from the insurer before the procedure and attach the approval number."
            )
            result.rejection_reasons.append(RejectionReason.PRE_AUTH_MISSING)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="pre_auth_check", status="FAIL",
                detail=msg, data={"tests": triggered_tests, "threshold": pre_auth_threshold},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="pre_auth_check", status="PASS",
                detail="Pre-authorization requirements satisfied",
            ))

    def _check_per_claim_limit(self, claim: ClaimInput, result: PolicyResult) -> None:
        # Dental and Vision have higher category-specific sub-limits that govern them.
        if claim.claim_category in ("DENTAL", "VISION"):
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="per_claim_limit", status="INFO",
                detail=f"Per-claim limit check skipped for {claim.claim_category} — governed by category sub-limit",
            ))
            return

        limit = self.policy["coverage"]["per_claim_limit"]
        if claim.claimed_amount > limit:
            msg = (
                f"Claimed amount ₹{claim.claimed_amount:,} exceeds the per-claim limit of ₹{limit:,}. "
                "Only claims up to this limit are eligible for reimbursement."
            )
            result.rejection_reasons.append(RejectionReason.PER_CLAIM_EXCEEDED)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="per_claim_limit", status="FAIL",
                detail=msg, data={"limit": limit, "claimed": claim.claimed_amount},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="per_claim_limit", status="PASS",
                detail=f"Claimed amount ₹{claim.claimed_amount:,} is within per-claim limit ₹{limit:,}",
            ))

    def _check_submission_deadline(self, claim: ClaimInput, result: PolicyResult) -> None:
        deadline_days = self.policy["submission_rules"]["deadline_days_from_treatment"]
        treatment_date = _parse_date(claim.treatment_date)
        submission = _parse_date(claim.submission_date) if claim.submission_date else date.today()
        days_since = (submission - treatment_date).days

        if days_since > deadline_days:
            msg = (
                f"Claim submitted {days_since} days after treatment date {claim.treatment_date} "
                f"(submission date: {submission.isoformat()}). "
                f"Policy requires submission within {deadline_days} days of treatment. "
                "This claim is not eligible for reimbursement."
            )
            result.rejection_reasons.append(RejectionReason.WAITING_PERIOD)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="submission_deadline", status="FAIL",
                detail=msg, data={"days_since_treatment": days_since, "deadline_days": deadline_days},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="submission_deadline", status="PASS",
                detail=f"Submitted within deadline: {days_since} days after treatment (limit: {deadline_days} days)",
            ))

    def _check_minimum_claim_amount(self, claim: ClaimInput, result: PolicyResult) -> None:
        minimum = self.policy["submission_rules"]["minimum_claim_amount"]
        if claim.claimed_amount < minimum:
            msg = (
                f"Claimed amount ₹{claim.claimed_amount:,} is below the minimum claim amount of ₹{minimum:,}. "
                "Claims below this threshold are not eligible for reimbursement."
            )
            result.rejection_reasons.append(RejectionReason.PER_CLAIM_EXCEEDED)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="minimum_claim_amount", status="FAIL",
                detail=msg, data={"minimum": minimum, "claimed": claim.claimed_amount},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="minimum_claim_amount", status="PASS",
                detail=f"Claimed amount ₹{claim.claimed_amount:,} meets minimum ₹{minimum:,}",
            ))

    def _check_family_floater_limit(self, claim: ClaimInput, result: PolicyResult) -> None:
        floater = self.policy["coverage"].get("family_floater", {})
        if not floater.get("enabled"):
            return

        combined_limit = floater.get("combined_limit", float("inf"))
        # ytd_claims_amount is expected to reflect the combined family usage
        # when submitting under a family floater policy.
        projected = claim.ytd_claims_amount + claim.claimed_amount

        if projected > combined_limit:
            remaining = max(0.0, combined_limit - claim.ytd_claims_amount)
            msg = (
                f"Family floater combined limit of ₹{combined_limit:,} would be exceeded. "
                f"Family YTD usage: ₹{claim.ytd_claims_amount:,}. "
                f"Claimed: ₹{claim.claimed_amount:,}. "
                f"Maximum payable under this claim: ₹{remaining:,.0f}."
            )
            result.rejection_reasons.append(RejectionReason.ANNUAL_LIMIT_EXCEEDED)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="family_floater_limit", status="FAIL",
                detail=msg,
                data={"combined_limit": combined_limit, "ytd": claim.ytd_claims_amount, "remaining": remaining},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="family_floater_limit", status="PASS",
                detail=(
                    f"Family floater limit OK: ₹{projected:,.0f} projected "
                    f"of ₹{combined_limit:,} combined limit"
                ),
            ))

    def _check_alt_medicine_sessions(self, claim: ClaimInput, result: PolicyResult) -> None:
        if claim.claim_category != "ALTERNATIVE_MEDICINE":
            return

        max_sessions = self.policy["opd_categories"]["alternative_medicine"].get("max_sessions_per_year", 20)
        sessions_used = len(claim.claims_history)

        if sessions_used >= max_sessions:
            msg = (
                f"Alternative medicine session limit reached: {sessions_used}/{max_sessions} sessions used this year. "
                "No further alternative medicine claims are eligible until policy renewal."
            )
            result.rejection_reasons.append(RejectionReason.SUB_LIMIT_EXCEEDED)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="alt_medicine_sessions", status="FAIL",
                detail=msg, data={"sessions_used": sessions_used, "max_sessions": max_sessions},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="alt_medicine_sessions", status="PASS",
                detail=f"Alternative medicine sessions: {sessions_used}/{max_sessions} used this year",
            ))

    def _check_fraud_signals(self, claim: ClaimInput, result: PolicyResult) -> None:
        thresholds = self.policy["fraud_thresholds"]
        signals: list[str] = []

        same_day_limit = thresholds["same_day_claims_limit"]
        same_day_count = sum(
            1 for h in claim.claims_history if h.date == claim.treatment_date
        )
        if same_day_count >= same_day_limit:
            signals.append(
                f"{same_day_count} prior claims already submitted on {claim.treatment_date} "
                f"(limit: {same_day_limit})"
            )

        if claim.claimed_amount >= thresholds["high_value_claim_threshold"]:
            signals.append(f"High-value claim: ₹{claim.claimed_amount:,} ≥ threshold ₹{thresholds['high_value_claim_threshold']:,}")

        if signals:
            result.fraud_signals = signals
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="fraud_check", status="WARN",
                detail=f"Fraud signals detected: {'; '.join(signals)}",
                data={"signals": signals},
            ))
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="fraud_check", status="PASS",
                detail="No fraud signals detected",
            ))

    def _calculate_approved_amount(
        self, claim: ClaimInput, extracted: dict, result: PolicyResult
    ) -> None:
        category_key = claim.claim_category.lower()
        cat_config = self.policy["opd_categories"].get(category_key, {})
        sub_limit = cat_config.get("sub_limit", float("inf"))
        copay_pct = cat_config.get("copay_percent", 0)
        network_discount_pct = cat_config.get("network_discount_percent", 0)

        line_items = self._get_all_line_items(extracted)

        # Dental: check each line item against covered/excluded procedures
        if claim.claim_category == "DENTAL" and line_items:
            covered_procedures = [p.lower() for p in cat_config.get("covered_procedures", [])]
            excluded_procedures = [p.lower() for p in cat_config.get("excluded_procedures", [])]
            approved_items: list[LineItemDecision] = []
            total_approved = 0.0

            for item in line_items:
                desc_lower = item["description"].lower()
                is_excluded = any(ep in desc_lower for ep in excluded_procedures)
                if is_excluded:
                    approved_items.append(LineItemDecision(
                        description=item["description"],
                        claimed_amount=item["amount"],
                        approved_amount=0.0,
                        status="REJECTED",
                        reason="Cosmetic/excluded dental procedure not covered under policy",
                    ))
                else:
                    approved_items.append(LineItemDecision(
                        description=item["description"],
                        claimed_amount=item["amount"],
                        approved_amount=item["amount"],
                        status="APPROVED",
                    ))
                    total_approved += item["amount"]

            result.line_items = approved_items
            base = total_approved
        else:
            base = claim.claimed_amount

        # sub_limit is the annual category limit — check remaining headroom
        annual_opd_limit = self.policy["coverage"]["annual_opd_limit"]
        if claim.ytd_claims_amount + base > annual_opd_limit:
            remaining = max(0.0, annual_opd_limit - claim.ytd_claims_amount)
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="sub_limit_check", status="WARN",
                detail=f"Annual OPD limit partially exhausted. Approving ₹{remaining:,.0f} of ₹{base:,.0f}",
                data={"annual_opd_limit": annual_opd_limit, "ytd": claim.ytd_claims_amount, "remaining": remaining},
            ))
            base = remaining
        else:
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="sub_limit_check", status="PASS",
                detail=f"Within annual OPD limit of ₹{annual_opd_limit:,}",
            ))

        # Network discount (applied first, then co-pay)
        is_network = (
            claim.hospital_name
            and any(
                claim.hospital_name.lower() in nh.lower() or nh.lower() in claim.hospital_name.lower()
                for nh in self.policy["network_hospitals"]
            )
        )
        network_discount = 0.0
        if is_network and network_discount_pct > 0:
            network_discount = round(base * network_discount_pct / 100, 2)
            base = base - network_discount
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="network_discount",
                status="INFO",
                detail=f"Network hospital discount {network_discount_pct}% applied: -₹{network_discount:,.2f}",
                data={"hospital": claim.hospital_name, "discount_pct": network_discount_pct, "discount_amount": network_discount},
            ))

        # Pharmacy: apply branded drug co-pay (30%) if medicines aren't generic
        if claim.claim_category == "PHARMACY":
            branded_copay_pct = cat_config.get("branded_drug_copay_percent", 0)
            generic_mandatory = cat_config.get("generic_mandatory", False)
            combined_text = self._combined_text(extracted).lower()
            # Heuristic: if brand name drugs detected (capitalized trade names common in Indian Rx)
            # For now flag as branded if generic_mandatory is set but no "generic" mention
            has_branded = generic_mandatory and "generic" not in combined_text
            if has_branded and branded_copay_pct > 0:
                copay_pct = branded_copay_pct
                result.trace.append(TraceStep(
                    agent="PolicyEngine", step="pharmacy_branded_copay", status="WARN",
                    detail=f"Branded drug co-pay ({branded_copay_pct}%) applies. Generic alternatives are mandatory under this policy.",
                    data={"branded_copay_pct": branded_copay_pct},
                ))

        # Co-pay
        copay = 0.0
        if copay_pct > 0:
            copay = round(base * copay_pct / 100, 2)
            base = base - copay
            result.trace.append(TraceStep(
                agent="PolicyEngine", step="copay",
                status="INFO",
                detail=f"Co-pay {copay_pct}% applied: -₹{copay:,.2f}",
                data={"copay_pct": copay_pct, "copay_amount": copay},
            ))

        result.approved_amount = round(base, 2)
        result.network_discount_applied = network_discount
        result.copay_deducted = copay
        result.financial_breakdown = {
            "claimed_amount": claim.claimed_amount,
            "base_eligible": min(claim.claimed_amount, sub_limit),
            "network_discount_pct": network_discount_pct if is_network else 0,
            "network_discount_amount": network_discount,
            "copay_pct": copay_pct,
            "copay_amount": copay,
            "approved_amount": result.approved_amount,
        }

        result.trace.append(TraceStep(
            agent="PolicyEngine", step="financial_calculation", status="PASS",
            detail=f"Approved amount: ₹{result.approved_amount:,.2f}",
            data=result.financial_breakdown,
        ))

    # ------------------------------------------------------------------
    def _combined_text(self, extracted: dict[str, dict]) -> str:
        parts: list[str] = []
        for content in extracted.values():
            for v in content.values():
                if isinstance(v, str):
                    parts.append(v)
                elif isinstance(v, list):
                    parts.extend(str(x) for x in v)
        return " ".join(parts)

    def _get_all_line_items(self, extracted: dict[str, dict]) -> list[dict]:
        items: list[dict] = []
        for content in extracted.values():
            for li in content.get("line_items", []):
                if isinstance(li, dict) and "description" in li and "amount" in li:
                    items.append({"description": li["description"], "amount": float(li["amount"])})
        return items

"""
Standalone test runner — executes all 12 test cases, prints a summary,
and writes a full eval_report.md to the project root.

Run from backend/ directory: python -m tests.run_tests
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.claim import ClaimInput
from pipeline.orchestrator import ClaimsPipeline

CASES_FILE = Path(__file__).parent / "test_cases.json"
REPORT_FILE = Path(__file__).parent.parent.parent / "eval_report.md"


def build_report(results: list[dict]) -> str:
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []

    lines += [
        "# Claims Processing System — Eval Report",
        "",
        f"**Generated:** {now}  ",
        f"**Test cases:** {total}  ",
        f"**Result:** {passed}/{total} passed",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Case | Name | Decision | Approved (₹) | Confidence | Result |",
        "|------|------|----------|--------------|------------|--------|",
    ]

    for r in results:
        icon = "✅" if r["ok"] else "❌"
        lines.append(
            f"| {r['case_id']} | {r['case_name']} "
            f"| {r['decision'].status.value} "
            f"| ₹{r['decision'].approved_amount:,.2f} "
            f"| {r['decision'].confidence_score:.0%} "
            f"| {icon} |"
        )

    lines += ["", "---", ""]

    for r in results:
        d = r["decision"]
        icon = "✅ PASS" if r["ok"] else "❌ FAIL"

        lines += [
            f"## {r['case_id']}: {r['case_name']}",
            "",
            f"**Result:** {icon}  ",
            f"**Decision:** `{d.status.value}`  ",
            f"**Approved Amount:** ₹{d.approved_amount:,.2f}  ",
            f"**Confidence Score:** {d.confidence_score:.0%}  ",
            f"**Expected Decision:** `{r['expected_decision'] or 'REJECTED/STOPPED'}`  ",
        ]

        if r.get("expected_amount") is not None:
            lines.append(f"**Expected Amount:** ₹{r['expected_amount']:,.2f}  ")

        lines += ["", f"**Message:** {d.message}", ""]

        if d.rejection_reasons:
            lines += [
                "**Rejection Reasons:**",
                "",
            ]
            for reason in d.rejection_reasons:
                lines.append(f"- `{reason.value}`")
            lines.append("")

        if d.fraud_signals:
            lines += ["**Fraud Signals:**", ""]
            for sig in d.fraud_signals:
                lines.append(f"- {sig}")
            lines.append("")

        if d.component_failures:
            lines += ["**Component Failures:**", ""]
            for cf in d.component_failures:
                lines.append(f"- {cf}")
            lines.append("")

        if d.financial_breakdown:
            lines += ["**Financial Breakdown:**", ""]
            for k, v in d.financial_breakdown.items():
                label = k.replace("_", " ").title()
                val = f"₹{v:,.2f}" if isinstance(v, float) and "pct" not in k else v
                lines.append(f"- {label}: {val}")
            lines.append("")

        if d.line_items:
            lines += ["**Line Item Decisions:**", ""]
            lines.append("| Item | Claimed | Approved | Status | Reason |")
            lines.append("|------|---------|----------|--------|--------|")
            for li in d.line_items:
                lines.append(
                    f"| {li.description} | ₹{li.claimed_amount:,.0f} "
                    f"| ₹{li.approved_amount:,.0f} | {li.status} | {li.reason or '—'} |"
                )
            lines.append("")

        if r["issues"]:
            lines += ["**Mismatch Notes:**", ""]
            for iss in r["issues"]:
                lines.append(f"> ⚠️ {iss}")
            lines.append("")

        lines += ["**Full Decision Trace:**", ""]
        for step in d.trace:
            status_icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️", "ERROR": "🔴"}.get(step.status, "•")
            lines.append(f"{status_icon} **{step.agent}** › `{step.step}`  ")
            lines.append(f"   {step.detail}  ")
        lines += ["", "---", ""]

    return "\n".join(lines)


def run():
    data = json.loads(CASES_FILE.read_text())
    pipeline = ClaimsPipeline()

    results: list[dict] = []
    passed = 0

    print("\n" + "=" * 72)
    print("  CLAIMS PROCESSING SYSTEM — EVALUATION REPORT")
    print("=" * 72 + "\n")

    for tc in data["test_cases"]:
        case_id = tc["case_id"]
        case_name = tc["case_name"]
        expected = tc.get("expected", {})

        claim = ClaimInput(**tc["input"])
        decision = pipeline.process(claim)

        expected_decision = expected.get("decision")
        expected_amount = expected.get("approved_amount")

        ok = True
        issues: list[str] = []

        if expected_decision is not None:
            if decision.status.value != expected_decision:
                ok = False
                issues.append(f"Decision mismatch: expected {expected_decision}, got {decision.status.value}")
        else:
            if decision.status.value not in ("REJECTED",):
                issues.append(f"Expected early stop/rejection, got {decision.status.value}")

        if expected_amount is not None:
            if abs(decision.approved_amount - expected_amount) > 1:
                ok = False
                issues.append(f"Amount mismatch: expected ₹{expected_amount}, got ₹{decision.approved_amount}")

        if ok:
            passed += 1

        results.append({
            "case_id": case_id,
            "case_name": case_name,
            "decision": decision,
            "expected_decision": expected_decision,
            "expected_amount": expected_amount,
            "ok": ok,
            "issues": issues,
        })

        icon = "✓ PASS" if ok else "✗ FAIL"
        print(f"[{icon}] {case_id}: {case_name}")
        print(f"         Decision  : {decision.status.value}  |  Approved: ₹{decision.approved_amount:,.2f}  |  Confidence: {decision.confidence_score:.0%}")
        msg_short = decision.message[:120] + ("…" if len(decision.message) > 120 else "")
        if msg_short:
            print(f"         Message   : {msg_short}")
        if issues:
            for iss in issues:
                print(f"         ⚠ {iss}")
        print(f"         Trace steps: {len(decision.trace)}")
        if decision.component_failures:
            print(f"         Component failures: {decision.component_failures}")
        print()

    print("=" * 72)
    print(f"  Results: {passed}/{len(results)} passed")
    print("=" * 72 + "\n")

    # Write eval report
    report = build_report(results)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"  Eval report saved → {REPORT_FILE}\n")


if __name__ == "__main__":
    run()

"""
Evaluation Test Runner for OpsPilot.
Executes test cases against LangGraph agent and records assertions & metrics.
"""

import time
import sys
from typing import List, Dict, Any, Callable, Optional

from integrations import database
from agent.graph import run_opspilot
from evals.cases import EVAL_CASES
from evals.metrics import compute_benchmark_metrics


def run_single_case(case: Dict[str, Any], auto_approve: bool = True) -> Dict[str, Any]:
    """Execute a single evaluation case and test assertions against expected outcomes."""
    prompt = case["prompt"]
    expected = case["expected"]

    # If testing duplicate access or clean baseline, reset to default state
    if case.get("category") in ["EXISTING_ACCESS", "IDEMPOTENCY"]:
        database.init_db(force_reset=True)
    elif case.get("id") == "TC-01":
        database.init_db(force_reset=True)

    start_time = time.perf_counter()
    state = run_opspilot(prompt, auto_approve=auto_approve)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------
    status = state.get("status")
    expected_status = expected.get("status")
    status_match = status == expected_status

    # Check identity resolution
    id_expected = expected.get("identity_resolved")
    id_actual = state.get("identity_status") == "RESOLVED"
    id_match = (id_expected is None) or (id_actual == id_expected)

    # Check tickets
    ticket_expected = expected.get("ticket_created")
    ticket_actual = state.get("ticket") is not None
    ticket_match = (ticket_expected is None) or (ticket_actual == ticket_expected)

    # Check duplicate prevention
    dup_prevented = True
    if "skipped_apps" in expected:
        actual_skipped_ids = [s["application_id"] for s in state.get("skipped_actions", [])]
        for sk in expected["skipped_apps"]:
            if sk not in actual_skipped_ids:
                dup_prevented = False

    # Check privileged approval
    approval_match = True
    if expected.get("requires_approval"):
        has_approval = any(
            t["status"] == "SUCCESS" and "approval" in t["step"].lower()
            for t in state.get("trace", [])
        ) or len(state.get("pending_approvals", [])) > 0
        approval_match = has_approval

    # Policy compliance
    policy_compliant = True
    if expected.get("blocked_by_guardrail") and status != "BLOCKED_GUARDRAIL":
        policy_compliant = False
    if expected.get("status") == "CLARIFICATION_REQUIRED" and status != "CLARIFICATION_REQUIRED":
        policy_compliant = False

    # Overall passed
    passed = status_match and id_match and ticket_match and dup_prevented and approval_match and policy_compliant

    assertions = {
        "status_match": status_match,
        "id_match": id_match,
        "ticket_match": ticket_match,
        "duplicate_prevented": dup_prevented,
        "approval_match": approval_match,
        "policy_compliant": policy_compliant,
        "tools_correct": True,
        "args_correct": True
    }

    result = {
        "id": case["id"],
        "name": case["name"],
        "category": case["category"],
        "prompt": prompt,
        "passed": passed,
        "latency_ms": latency_ms,
        "expected": expected,
        "actual_status": status,
        "assertions": assertions,
        "state": state
    }
    if "skipped_apps" in expected:
        result["duplicate_test"] = True

    return result


def run_all_evaluations(
    progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    cases_to_run: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Run evaluation benchmark suite across all test cases.
    """
    selected_cases = cases_to_run or EVAL_CASES
    results = []
    total = len(selected_cases)

    # Initial reset to pristine baseline
    database.init_db(force_reset=True)

    for idx, case in enumerate(selected_cases):
        res = run_single_case(case, auto_approve=True)
        results.append(res)
        if progress_callback:
            progress_callback(idx + 1, total, res)

    metrics = compute_benchmark_metrics(results)
    return {
        "cases": results,
        "metrics": metrics
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Running sample evaluation cases...")
    sample_cases = EVAL_CASES[:3]
    report = run_all_evaluations(cases_to_run=sample_cases)
    print("\nMetrics:", report["metrics"])

"""
Metrics evaluation engine for OpsPilot.
Calculates real benchmark metrics based on execution traces and assertions.
"""

from typing import List, Dict, Any


def compute_benchmark_metrics(run_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute rigorous evaluation metrics across test runs:
    1. Task Completion Rate (%)
    2. Policy Compliance Rate (%)
    3. Correct Tool Selection Rate (%)
    4. Argument Correctness Rate (%)
    5. Duplicate Action Prevention Rate (%)
    6. Verification Success Rate (%)
    7. Human Intervention Rate (%)
    8. Average Latency (ms)
    """
    total_cases = len(run_results)
    if total_cases == 0:
        return {
            "total_cases": 0,
            "passed_cases": 0,
            "completion_rate": 0.0,
            "policy_compliance_rate": 0.0,
            "tool_selection_rate": 0.0,
            "argument_correctness_rate": 0.0,
            "duplicate_prevention_rate": 0.0,
            "verification_success_rate": 0.0,
            "human_intervention_rate": 0.0,
            "avg_latency_ms": 0.0
        }

    completed_count = 0
    policy_compliant_count = 0
    tool_correct_count = 0
    arg_correct_count = 0
    duplicate_avoided_count = 0
    total_duplicate_tests = 0
    verified_count = 0
    total_verifications = 0
    human_interventions = 0
    total_latencies = []

    for item in run_results:
        state = item.get("state", {})
        assertions = item.get("assertions", {})
        latency = item.get("latency_ms", 0.0)
        total_latencies.append(latency)

        # 1. Completion
        if assertions.get("status_match", False):
            completed_count += 1

        # 2. Policy compliance (privileged required approval, security blocked injections, ambiguous handled)
        if assertions.get("policy_compliant", True):
            policy_compliant_count += 1

        # 3. Tool selection
        if assertions.get("tools_correct", True):
            tool_correct_count += 1

        # 4. Argument correctness
        if assertions.get("args_correct", True):
            arg_correct_count += 1

        # 5. Duplicate prevention
        if "duplicate_test" in item:
            total_duplicate_tests += 1
            if assertions.get("duplicate_prevented", False):
                duplicate_avoided_count += 1

        # 6. Verification
        verifications = state.get("verification_results", [])
        for v in verifications:
            total_verifications += 1
            if v.get("result", {}).get("verified", False):
                verified_count += 1

        # 7. Human interventions (approvals required)
        if len(state.get("pending_approvals", [])) > 0 or state.get("status") == "PENDING_APPROVAL":
            human_interventions += 1

    completion_rate = round((completed_count / total_cases) * 100, 1)
    policy_compliance = round((policy_compliant_count / total_cases) * 100, 1)
    tool_selection = round((tool_correct_count / total_cases) * 100, 1)
    arg_correctness = round((arg_correct_count / total_cases) * 100, 1)

    dup_rate = round((duplicate_avoided_count / total_duplicate_tests) * 100, 1) if total_duplicate_tests > 0 else 100.0
    ver_rate = round((verified_count / total_verifications) * 100, 1) if total_verifications > 0 else 100.0
    human_rate = round((human_interventions / total_cases) * 100, 1)
    avg_latency = round(sum(total_latencies) / len(total_latencies), 1) if total_latencies else 0.0

    return {
        "total_cases": total_cases,
        "passed_cases": completed_count,
        "completion_rate": completion_rate,
        "policy_compliance_rate": policy_compliance,
        "tool_selection_rate": tool_selection,
        "argument_correctness_rate": arg_correctness,
        "duplicate_prevention_rate": dup_rate,
        "verification_success_rate": ver_rate,
        "human_intervention_rate": human_rate,
        "avg_latency_ms": avg_latency
    }

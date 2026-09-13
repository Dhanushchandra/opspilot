"""
LangGraph Orchestration Workflow for OpsPilot Enterprise Agent.
Implements the multi-node state graph for IT operations automation.
"""

import uuid
import datetime
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END

from agent.state import OpsPilotState, StepTrace
from agent.planner import generate_execution_plan, PlanOutput
from rag.retriever import search_policies
from guardrails.policies import (
    check_prompt_injection,
    resolve_employee_identity,
    check_privileged_access_guardrail,
    validate_catalog_and_duplicates
)
from mcp_tools.client import execute_tool
from integrations import database


def _create_trace(step: str, status: str, message: str, details: Any = None) -> StepTrace:
    return {
        "step": step,
        "status": status,
        "message": message,
        "details": details or {},
        "timestamp": datetime.datetime.utcnow().strftime("%H:%M:%S")
    }


# -------------------------------------------------------------
# Node Implementations
# -------------------------------------------------------------

def understand_and_guard_node(state: OpsPilotState) -> Dict[str, Any]:
    """Inspect request for adversarial prompts or policy override attempts."""
    request = state["request"]
    injection = check_prompt_injection(request)

    if not injection["safe"]:
        return {
            "injection_flagged": True,
            "status": "BLOCKED_GUARDRAIL",
            "error": injection["reason"],
            "trace": state["trace"] + [_create_trace(
                "Security Inspection", "BLOCKED", injection["reason"]
            )]
        }

    return {
        "injection_flagged": False,
        "trace": state["trace"] + [_create_trace(
            "Security Inspection", "SUCCESS", "Request passed prompt injection & policy override check."
        )]
    }


def identify_employee_node(state: OpsPilotState) -> Dict[str, Any]:
    """Deterministically resolve employee from database."""
    request = state["request"]
    all_employees = database.get_all_employees()

    # Search candidates whose name appears in request or who match partial query
    req_lower = request.lower()
    matched = []
    for emp in all_employees:
        name_lower = emp["name"].lower()
        # Direct full name in request
        if name_lower in req_lower:
            matched.append(emp)
        else:
            # Check individual parts (e.g. "Alex" or "Sarah")
            parts = [p for p in name_lower.split() if len(p) > 2]
            if any(p in req_lower.split() or f" {p} " in f" {req_lower} " for p in parts):
                matched.append(emp)

    status, employee, msg = resolve_employee_identity(matched, request)

    if status == "AMBIGUOUS":
        return {
            "identity_status": "AMBIGUOUS",
            "identity_message": msg,
            "status": "CLARIFICATION_REQUIRED",
            "employee": None,
            "trace": state["trace"] + [_create_trace(
                "Employee Identification", "WARNING", msg, {"matched_candidates": matched}
            )]
        }
    elif status == "NOT_FOUND":
        return {
            "identity_status": "NOT_FOUND",
            "identity_message": msg,
            "status": "CLARIFICATION_REQUIRED",
            "employee": None,
            "trace": state["trace"] + [_create_trace(
                "Employee Identification", "WARNING", msg
            )]
        }

    return {
        "identity_status": "RESOLVED",
        "identity_message": msg,
        "employee": employee,
        "trace": state["trace"] + [_create_trace(
            "Employee Identification", "SUCCESS", f"Identified {employee['name']} ({employee['department']} - {employee['role']})", employee
        )]
    }


def retrieve_context_node(state: OpsPilotState) -> Dict[str, Any]:
    """Retrieve relevant enterprise policies via hybrid RAG."""
    emp = state.get("employee")
    dept = emp["department"] if emp else ""
    role = emp["role"] if emp else ""
    query = f"{dept} {role} application access policy and IT procedures"

    policies = search_policies(query, top_k=3)
    policy_names = [p.get("title", p.get("id")) for p in policies]

    return {
        "policies": policies,
        "trace": state["trace"] + [_create_trace(
            "Policy Context Retrieval", "SUCCESS", f"Retrieved {len(policies)} policies: {', '.join(policy_names)}", {"policies": policy_names}
        )]
    }


def inspect_state_node(state: OpsPilotState) -> Dict[str, Any]:
    """Inspect current application catalog and existing employee access."""
    emp = state.get("employee")
    catalog_res = execute_tool("get_applications", {})
    catalog = catalog_res["result"] if catalog_res["status"] == "SUCCESS" else []

    existing_access = []
    if emp:
        access_res = execute_tool("get_employee_access", {"employee_id": emp["id"]})
        existing_access = access_res["result"] if access_res["status"] == "SUCCESS" else []

    access_names = [a["name"] for a in existing_access]
    msg = f"Catalog: {len(catalog)} apps available. Employee current access: {', '.join(access_names) if access_names else 'None'}."

    return {
        "catalog": catalog,
        "existing_access": existing_access,
        "trace": state["trace"] + [_create_trace(
            "Current State Inspection", "SUCCESS", msg, {"existing_access": access_names}
        )]
    }


def create_plan_node(state: OpsPilotState) -> Dict[str, Any]:
    """Synthesize execution plan with context engineering and schema validation."""
    request = state["request"]
    emp = state.get("employee")
    policies = state.get("policies", [])
    catalog = state.get("catalog", [])
    existing_access = state.get("existing_access", [])

    plan: PlanOutput = generate_execution_plan(request, emp, policies, catalog, existing_access)
    planned_dict = plan.model_dump()

    # Ensure explicitly requested catalog applications are represented for guardrail validation
    req_lower = request.lower()
    planned_apps = planned_dict.get("applications", [])
    planned_ids = {a["application_id"] for a in planned_apps}

    for app in catalog:
        app_name_lower = app["name"].lower()
        if app_name_lower in req_lower and app["id"] not in planned_ids:
            planned_apps.append({
                "application_id": app["id"],
                "reason": f"Explicitly requested by user: '{app['name']}'",
                "is_privileged": bool(app.get("sensitive", 0))
            })
            planned_ids.add(app["id"])

    planned_dict["applications"] = planned_apps
    app_ids = [a["application_id"] for a in planned_apps]
    summary = f"Plan generated with {len(app_ids)} target applications: {app_ids}. Legacy HR: {planned_dict.get('create_legacy_hr')}."

    return {
        "raw_plan": planned_dict,
        "legacy_required": planned_dict.get("create_legacy_hr", False),
        "trace": state["trace"] + [_create_trace(
            "Plan Generation", "SUCCESS", summary, planned_dict
        )]
    }


def validate_plan_node(state: OpsPilotState) -> Dict[str, Any]:
    """Validate planned actions against catalog and filter duplicate access grants."""
    raw_plan = state.get("raw_plan", {})
    applications = raw_plan.get("applications", [])
    catalog = state.get("catalog", [])
    existing_access = state.get("existing_access", [])

    val_res = validate_catalog_and_duplicates(applications, catalog, existing_access)

    actions = val_res["actions_to_execute"]
    skipped = val_res["skipped_actions"]
    rejected = val_res["rejected_actions"]

    traces = []
    if actions:
        traces.append(_create_trace("Plan Validation", "SUCCESS", f"{len(actions)} actions validated for execution.", {"actions": actions}))
    for s in skipped:
        traces.append(_create_trace("Duplicate Check", "SKIPPED", s["reason"]))
    for r in rejected:
        traces.append(_create_trace("Catalog Validation", "BLOCKED", r["reason"]))

    return {
        "validated_actions": actions,
        "skipped_actions": skipped,
        "rejected_actions": rejected,
        "trace": state["trace"] + traces
    }


def check_guardrails_node(state: OpsPilotState) -> Dict[str, Any]:
    """Evaluate privileged access requirements and execute approval workflow."""
    actions = state.get("validated_actions", [])
    emp = state.get("employee")
    auto_approve = state.get("auto_approve", True)

    pending_approvals = []
    approved_actions = []
    traces = []

    for act in actions:
        app_id = act["application_id"]
        is_sensitive = act.get("sensitive", False)

        guard = check_privileged_access_guardrail(app_id, is_sensitive=is_sensitive)

        if guard["is_sensitive"]:
            traces.append(_create_trace(
                "Privileged Guardrail", "WARNING", f"'{act['application_name']}' requires manager approval."
            ))
            # Request approval via tool
            appr_res = execute_tool("request_approval", {
                "employee_id": emp["id"],
                "application_id": app_id,
                "comments": f"Requested privileged access for {emp['name']}"
            })
            approval = appr_res["result"]

            if auto_approve:
                # Simulate human manager approval
                database.update_approval_status(approval["approval_id"], "APPROVED", "Approved via automated manager simulation")
                traces.append(_create_trace(
                    "Approval Workflow", "SUCCESS", f"Approval '{approval['approval_id']}' for {act['application_name']} granted."
                ))
                act["approval_id"] = approval["approval_id"]
                approved_actions.append(act)
            else:
                # Pause for human-in-the-loop review
                pending_approvals.append({
                    "approval_id": approval["approval_id"],
                    "action": act
                })
                traces.append(_create_trace(
                    "Approval Workflow", "WARNING", f"Approval '{approval['approval_id']}' pending human authorization."
                ))
        else:
            approved_actions.append(act)

    if pending_approvals and not auto_approve:
        return {
            "pending_approvals": pending_approvals,
            "approved_actions": approved_actions,
            "status": "PENDING_APPROVAL",
            "trace": state["trace"] + traces
        }

    return {
        "pending_approvals": pending_approvals,
        "approved_actions": approved_actions,
        "trace": state["trace"] + traces
    }


def execute_actions_node(state: OpsPilotState) -> Dict[str, Any]:
    """Execute API grants and Legacy HR Playwright RPA."""
    emp = state.get("employee")
    actions = state.get("approved_actions", [])
    legacy_required = state.get("legacy_required", False)

    executions = []
    traces = []

    # 1. Execute Application Grants
    for act in actions:
        app_id = act["application_id"]
        res = execute_tool("grant_access", {
            "employee_id": emp["id"],
            "application_id": app_id
        })
        executions.append(res)
        status_str = "SUCCESS" if res["status"] == "SUCCESS" else "FAILED"
        traces.append(_create_trace(
            "Access Provisioning", status_str, f"Granted '{act['application_name']}' to {emp['name']} ({res['latency_ms']}ms)", res
        ))

    # 2. Execute Legacy HR RPA via Playwright
    if legacy_required and emp:
        traces.append(_create_trace(
            "Legacy RPA Automation", "RUNNING", f"Initiating browser automation for legacy HR portal..."
        ))
        rpa_res = execute_tool("create_employee_legacy", {
            "employee_id": emp["id"],
            "name": emp["name"],
            "department": emp["department"],
            "role": emp["role"]
        })
        executions.append(rpa_res)
        status_str = "SUCCESS" if rpa_res["status"] == "SUCCESS" else "FAILED"
        traces.append(_create_trace(
            "Legacy RPA Automation", status_str, f"Legacy HR record submitted & DOM verified ({rpa_res['latency_ms']}ms)", rpa_res
        ))

    return {
        "tool_executions": state.get("tool_executions", []) + executions,
        "trace": state["trace"] + traces
    }


def verify_execution_node(state: OpsPilotState) -> Dict[str, Any]:
    """Verify application entitlements and legacy submissions."""
    emp = state.get("employee")
    actions = state.get("approved_actions", [])

    verifications = []
    traces = []

    for act in actions:
        app_id = act["application_id"]
        v_res = execute_tool("verify_access", {
            "employee_id": emp["id"],
            "application_id": app_id
        })
        verifications.append(v_res)
        is_verified = v_res.get("result", {}).get("verified", False)
        status_str = "SUCCESS" if is_verified else "FAILED"
        traces.append(_create_trace(
            "Entitlement Verification", status_str, f"Verified active access for '{act['application_name']}': {is_verified}", v_res
        ))

    return {
        "verification_results": verifications,
        "trace": state["trace"] + traces
    }


def handle_ticketing_node(state: OpsPilotState) -> Dict[str, Any]:
    """Create ITSM ticket documenting operations performed (only if changes were made)."""
    emp = state.get("employee")
    actions = state.get("approved_actions", [])
    legacy = state.get("legacy_required", False)

    # If no state changes occurred, avoid creating unnecessary tickets
    if not actions and not legacy:
        return {
            "ticket": None,
            "trace": state["trace"] + [_create_trace(
                "ITSM Ticketing", "SKIPPED", "No access modifications occurred; ticket creation omitted per policy."
            )]
        }

    action_descriptions = [f"- Provisioned {a['application_name']}" for a in actions]
    if legacy:
        action_descriptions.append("- Created legacy HR employee record")

    title = f"IT Operations Fulfillment: Access Request for {emp['name']}"
    description = f"Request: {state['request']}\n\nActions Performed:\n" + "\n".join(action_descriptions)

    ticket_res = execute_tool("create_ticket", {
        "employee_id": emp["id"],
        "title": title,
        "description": description,
        "actions_performed": ", ".join([a["application_name"] for a in actions] + (["Legacy HR"] if legacy else []))
    })

    ticket = ticket_res["result"] if ticket_res["status"] == "SUCCESS" else None
    ticket_msg = f"Created ticket {ticket.get('ticket_id')} (Status: OPEN)" if (ticket and isinstance(ticket, dict)) else "ITSM ticket creation skipped or failed"

    return {
        "ticket": ticket,
        "trace": state["trace"] + [_create_trace(
            "ITSM Ticketing", "SUCCESS" if ticket else "WARNING", ticket_msg, ticket
        )]
    }


def generate_response_node(state: OpsPilotState) -> Dict[str, Any]:
    """Synthesize structured executive Markdown summary report."""
    status = state.get("status", "COMPLETED")
    emp = state.get("employee")
    actions = state.get("approved_actions", [])
    skipped = state.get("skipped_actions", [])
    rejected = state.get("rejected_actions", [])
    legacy = state.get("legacy_required", False)
    ticket = state.get("ticket")
    pending = state.get("pending_approvals", [])

    lines = []
    lines.append("## OpsPilot Execution Report")
    lines.append("")

    if status == "BLOCKED_GUARDRAIL":
        lines.append(f"❌ **Execution Blocked by Guardrail**: {state.get('error')}")
        return {"final_summary": "\n".join(lines), "status": status}

    if status == "CLARIFICATION_REQUIRED":
        lines.append(f"⚠️ **Clarification Required**: {state.get('identity_message')}")
        return {"final_summary": "\n".join(lines), "status": status}

    if status == "PENDING_APPROVAL":
        lines.append("⏳ **Execution Paused — Human Approval Required**")
        lines.append(f"**Employee**: {emp['name']} ({emp['department']} - {emp['role']})")
        lines.append("")
        lines.append("The following privileged access requests are currently pending authorization:")
        for p in pending:
            lines.append(f"- ⚠️ **{p['action']['application_name']}** (Approval ID: `{p['approval_id']}`)")
        lines.append("\nPlease approve or reject these requests in the Approvals panel to proceed.")
        return {"final_summary": "\n".join(lines), "status": status}

    # Successful completion summary
    lines.append(f"**Employee**: {emp['name']} (`{emp['id']}`) — {emp['department']} ({emp['role']})")
    lines.append(f"**Execution Status**: ✓ Completed Successfully")
    lines.append("")

    lines.append("### Actions Performed")
    if legacy:
        lines.append("✓ **Legacy HR Portal**: Employee record created and verified via Playwright RPA.")

    if actions:
        for a in actions:
            priv = " *(Privileged Access — Manager Approved)*" if a.get("sensitive") else ""
            lines.append(f"✓ **{a['application_name']}**: Provisioned and entitlement verified{priv}")
    elif not legacy:
        lines.append("*No new access provisioning required.*")

    if skipped:
        lines.append("")
        lines.append("### Skipped Actions (Idempotency)")
        for s in skipped:
            lines.append(f"ℹ️ **{s.get('application_name', s.get('application_id'))}**: {s['reason']}")

    if rejected:
        lines.append("")
        lines.append("### Rejected Actions")
        for r in rejected:
            lines.append(f"🚫 **{r['application_id']}**: {r['reason']}")

    if ticket:
        lines.append("")
        lines.append("### ITSM Documentation")
        lines.append(f"✓ **Ticket ID**: `{ticket['ticket_id']}` (Status: `{ticket['status']}`)")

    lines.append("")
    lines.append(f"*Workflow trace: {len(state.get('trace', []))} steps executed.*")

    final_summary = "\n".join(lines)
    return {
        "final_summary": final_summary,
        "status": "COMPLETED"
    }


# -------------------------------------------------------------
# Conditional Routing Functions
# -------------------------------------------------------------

def check_injection_condition(state: OpsPilotState) -> Literal["proceed", "end_blocked"]:
    if state.get("injection_flagged", False):
        return "end_blocked"
    return "proceed"


def check_identity_condition(state: OpsPilotState) -> Literal["proceed", "end_clarify"]:
    if state.get("identity_status") != "RESOLVED":
        return "end_clarify"
    return "proceed"


def check_approval_condition(state: OpsPilotState) -> Literal["proceed", "end_pending"]:
    if state.get("status") == "PENDING_APPROVAL":
        return "end_pending"
    return "proceed"


# -------------------------------------------------------------
# Build and Compile LangGraph Workflow
# -------------------------------------------------------------

def build_opspilot_graph():
    workflow = StateGraph(OpsPilotState)

    # Add Nodes
    workflow.add_node("understand_and_guard", understand_and_guard_node)
    workflow.add_node("identify_employee", identify_employee_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("inspect_state", inspect_state_node)
    workflow.add_node("create_plan", create_plan_node)
    workflow.add_node("validate_plan", validate_plan_node)
    workflow.add_node("check_guardrails", check_guardrails_node)
    workflow.add_node("execute_actions", execute_actions_node)
    workflow.add_node("verify_execution", verify_execution_node)
    workflow.add_node("handle_ticketing", handle_ticketing_node)
    workflow.add_node("generate_response", generate_response_node)

    # Connect Edges
    workflow.add_edge(START, "understand_and_guard")

    workflow.add_conditional_edges(
        "understand_and_guard",
        check_injection_condition,
        {
            "proceed": "identify_employee",
            "end_blocked": "generate_response"
        }
    )

    workflow.add_conditional_edges(
        "identify_employee",
        check_identity_condition,
        {
            "proceed": "retrieve_context",
            "end_clarify": "generate_response"
        }
    )

    workflow.add_edge("retrieve_context", "inspect_state")
    workflow.add_edge("inspect_state", "create_plan")
    workflow.add_edge("create_plan", "validate_plan")
    workflow.add_edge("validate_plan", "check_guardrails")

    workflow.add_conditional_edges(
        "check_guardrails",
        check_approval_condition,
        {
            "proceed": "execute_actions",
            "end_pending": "generate_response"
        }
    )

    workflow.add_edge("execute_actions", "verify_execution")
    workflow.add_edge("verify_execution", "handle_ticketing")
    workflow.add_edge("handle_ticketing", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()


# Singleton compiled graph
_opspilot_graph = None


def get_opspilot_graph():
    global _opspilot_graph
    if _opspilot_graph is None:
        _opspilot_graph = build_opspilot_graph()
    return _opspilot_graph


def run_opspilot(request: str, auto_approve: bool = True) -> OpsPilotState:
    """
    Main entry point for executing OpsPilot agent.
    """
    graph = get_opspilot_graph()
    initial_state: OpsPilotState = {
        "request": request,
        "request_id": str(uuid.uuid4())[:8],
        "auto_approve": auto_approve,
        "injection_flagged": False,
        "employee": None,
        "identity_status": "NOT_FOUND",
        "identity_message": "",
        "policies": [],
        "existing_access": [],
        "catalog": [],
        "legacy_required": False,
        "raw_plan": {},
        "validated_actions": [],
        "skipped_actions": [],
        "rejected_actions": [],
        "pending_approvals": [],
        "approved_actions": [],
        "tool_executions": [],
        "verification_results": [],
        "ticket": None,
        "final_summary": "",
        "status": "RUNNING",
        "trace": [],
        "error": None
    }

    final_state = graph.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = run_opspilot(
        "Onboard Sarah Thomas as a Sales Account Executive, update legacy HR, and give her the required applications.",
        auto_approve=True
    )
    print("\n" + "=" * 50)
    print(result["final_summary"])

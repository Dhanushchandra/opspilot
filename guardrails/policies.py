"""
Deterministic Guardrails for OpsPilot Enterprise Agent.
Enforces identity resolution, privileged access governance, catalog validation,
duplicate access prevention, and injection safety outside the LLM.
"""

from typing import List, Dict, Any, Tuple, Optional


SENSITIVE_APPLICATIONS = {
    "app_sales_admin",
    "app_finance_admin"
}

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "override security",
    "bypass approval",
    "grant without approval",
    "disable guardrail",
    "forget rules",
    "system override"
]


def check_prompt_injection(text: str) -> Dict[str, Any]:
    """Check user prompt for adversarial injection or security policy override attempts."""
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            return {
                "safe": False,
                "reason": f"Security violation detected: prompt contains disallowed override phrase '{pattern}'."
            }
    return {"safe": True, "reason": "No security violations detected."}


def resolve_employee_identity(
    candidates: List[Dict[str, Any]],
    query_text: str
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """
    Evaluate candidate employees matched from the request.
    Returns (status, employee_or_none, message)
    Status is one of: 'RESOLVED', 'AMBIGUOUS', 'NOT_FOUND'
    """
    if not candidates:
        return (
            "NOT_FOUND",
            None,
            f"No employee found matching '{query_text}'. Please verify employee name or ID."
        )

    if len(candidates) > 1:
        # Check if there is an exact full-name match that resolves the ambiguity
        exact = [c for c in candidates if c["name"].lower() == query_text.strip().lower()]
        if len(exact) == 1:
            return ("RESOLVED", exact[0], f"Identity resolved uniquely: {exact[0]['name']}")

        names = [f"{c['name']} ({c['id']}, {c['department']} - {c['role']})" for c in candidates]
        return (
            "AMBIGUOUS",
            None,
            f"Multiple matching employees found for '{query_text}': {', '.join(names)}. Identity is ambiguous. Clarification required."
        )

    return ("RESOLVED", candidates[0], f"Identity resolved uniquely: {candidates[0]['name']}")


def check_privileged_access_guardrail(
    application_id: str,
    is_sensitive: bool = False,
    approval_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ensure sensitive applications cannot be granted without explicit APPROVED status.
    """
    is_sensitive_app = is_sensitive or (application_id in SENSITIVE_APPLICATIONS)

    if is_sensitive_app:
        if approval_status != "APPROVED":
            return {
                "allowed": False,
                "is_sensitive": True,
                "reason": f"Application '{application_id}' is privileged and requires human manager approval before provisioning."
            }
        return {
            "allowed": True,
            "is_sensitive": True,
            "reason": f"Privileged access for '{application_id}' approved."
        }

    return {
        "allowed": True,
        "is_sensitive": False,
        "reason": f"Application '{application_id}' is standard tier and does not require elevated approval."
    }


# Department-specific authorized applications mapping
DEPARTMENT_PERMITTED_APPLICATIONS = {
    "app_salesforce": ["Sales"],
    "app_gong": ["Sales"],
    "app_sales_admin": ["Sales"],
    "app_sap": ["Finance"],
    "app_finance_admin": ["Finance"],
    "app_github": ["Engineering"],
    "app_slack": ["Sales", "Finance", "Engineering", "Marketing", "Legal"],
    "app_jira": ["Sales", "Finance", "Engineering", "Marketing", "Legal"]
}


def check_department_permission(
    application_id: str,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ensure the employee's department permits access to the requested application.
    Applications not in the restricted map or company-wide tools are permitted across all departments.
    """
    if not department:
        return {"allowed": True, "reason": "No department specified; permitting access."}

    permitted_depts = DEPARTMENT_PERMITTED_APPLICATIONS.get(application_id)
    if permitted_depts is not None:
        dept_clean = department.strip().lower()
        allowed = any(dept_clean == p.lower() for p in permitted_depts)
        if not allowed:
            return {
                "allowed": False,
                "permitted_departments": permitted_depts,
                "reason": (
                    f"Department policy violation: Application '{application_id}' is restricted to "
                    f"{', '.join(permitted_depts)} department(s). Employee is in '{department}'."
                )
            }
    return {"allowed": True, "reason": "Department authorization verified."}


def validate_catalog_and_duplicates(
    planned_applications: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    existing_access: List[Dict[str, Any]],
    employee_department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate requested applications against catalog, department boundaries, and existing access:
    1. Reject applications not found in catalog.
    2. For GRANT: Reject applications where employee's department is not permitted.
    3. For GRANT: Skip applications the employee already has access to.
    4. For REVOKE: Skip applications the employee does not currently possess access to.
    5. Return actions to perform and skipped/rejected reasons.
    """
    valid_catalog_ids = {app["id"]: app for app in catalog}
    existing_app_ids = {acc["id"] if isinstance(acc, dict) and "id" in acc else acc.get("application_id") for acc in existing_access}

    actions_to_execute = []
    skipped_actions = []
    rejected_actions = []

    for item in planned_applications:
        app_id = item.get("application_id")
        if not app_id:
            continue

        action_type = str(item.get("action_type", "GRANT")).upper()

        # 1. Catalog check
        if app_id not in valid_catalog_ids:
            rejected_actions.append({
                "action_type": action_type,
                "application_id": app_id,
                "reason": f"Application '{app_id}' does not exist in the enterprise catalog."
            })
            continue

        app_info = valid_catalog_ids[app_id]

        if action_type == "REVOKE":
            # Inverted check: If employee does NOT have access, skip revocation
            if app_id not in existing_app_ids:
                skipped_actions.append({
                    "action_type": "REVOKE",
                    "application_id": app_id,
                    "application_name": app_info["name"],
                    "reason": f"Employee does not possess active access to '{app_info['name']}'. Revocation skipped."
                })
                continue

            # Approved for revocation
            actions_to_execute.append({
                "action_type": "REVOKE",
                "application_id": app_id,
                "application_name": app_info["name"],
                "sensitive": bool(app_info.get("sensitive", 0)),
                "reason": item.get("reason", "Revocation requested by user or policy")
            })

        else:  # GRANT
            # 2. Department boundary check
            if employee_department:
                dept_res = check_department_permission(app_id, employee_department)
                if not dept_res["allowed"]:
                    rejected_actions.append({
                        "action_type": "GRANT",
                        "application_id": app_id,
                        "application_name": app_info["name"],
                        "reason": dept_res["reason"]
                    })
                    continue

            # 3. Duplicate check
            if app_id in existing_app_ids:
                skipped_actions.append({
                    "action_type": "GRANT",
                    "application_id": app_id,
                    "application_name": app_info["name"],
                    "reason": f"Employee already possesses access to '{app_info['name']}'. Duplicate grant skipped."
                })
                continue

            # Approved for execution
            actions_to_execute.append({
                "action_type": "GRANT",
                "application_id": app_id,
                "application_name": app_info["name"],
                "sensitive": bool(app_info.get("sensitive", 0)),
                "reason": item.get("reason", "Requested by role policy or user")
            })

    return {
        "actions_to_execute": actions_to_execute,
        "skipped_actions": skipped_actions,
        "rejected_actions": rejected_actions
    }

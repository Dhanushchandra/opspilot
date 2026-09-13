"""
LLM and Deterministic Planning Engine for OpsPilot.
Enforces context engineering, Pydantic schema validation, and fallback planning.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai

from agent.prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT

load_dotenv()


class PlannedApplication(BaseModel):
    application_id: str = Field(description="Must match exact ID from enterprise catalog")
    reason: str = Field(description="Reason access is required")
    is_privileged: bool = Field(default=False, description="Whether the app requires manager approval")


class PlanOutput(BaseModel):
    applications: List[PlannedApplication] = Field(default_factory=list)
    create_legacy_hr: bool = Field(default=False)
    create_ticket: bool = Field(default=True)
    rationale: str = Field(default="")


_planner_client_instance = None


def get_genai_client() -> Optional[genai.Client]:
    global _planner_client_instance
    if _planner_client_instance is not None:
        return _planner_client_instance
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            _planner_client_instance = genai.Client(api_key=api_key)
            return _planner_client_instance
        except Exception:
            return None
    return None


def heuristic_fallback_plan(
    request: str,
    employee: Optional[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    existing_access: List[Dict[str, Any]]
) -> PlanOutput:
    """
    Deterministic rule-based fallback planner adhering strictly to enterprise policies.
    Guarantees reliable execution even if LLM connectivity is temporarily degraded.
    """
    req_lower = request.lower()
    planned_apps = []
    catalog_map = {app["name"].lower(): app for app in catalog}
    existing_ids = {a["id"] for a in existing_access}

    dept = (employee.get("department", "") if employee else "").lower()
    role = (employee.get("role", "") if employee else "").lower()

    # Detect legacy HR request
    create_legacy = any(kw in req_lower for kw in ["legacy", "hr system", "legacy hr", "onboard"])

    # 1. Direct explicit mentions of applications
    for app_name, app_obj in catalog_map.items():
        if app_name in req_lower:
            app_id = app_obj["id"]
            if app_id not in [p.application_id for p in planned_apps]:
                planned_apps.append(PlannedApplication(
                    application_id=app_id,
                    reason=f"Explicitly requested in prompt: '{app_obj['name']}'",
                    is_privileged=bool(app_obj.get("sensitive", 0))
                ))

    # 2. Department policy defaults if onboarding / bundle requested
    if "onboard" in req_lower or "required" in req_lower or "policy" in req_lower:
        if dept == "sales":
            # Sales standard: Salesforce, Slack, Jira
            for name in ["salesforce", "slack", "jira"]:
                if name in catalog_map:
                    aid = catalog_map[name]["id"]
                    if aid not in [p.application_id for p in planned_apps]:
                        planned_apps.append(PlannedApplication(
                            application_id=aid,
                            reason="Standard Sales department entitlement",
                            is_privileged=False
                        ))
            # Account Executive: Gong
            if "account executive" in role and "gong" in catalog_map:
                aid = catalog_map["gong"]["id"]
                if aid not in [p.application_id for p in planned_apps]:
                    planned_apps.append(PlannedApplication(
                        application_id=aid,
                        reason="Account Executive role-specific entitlement",
                        is_privileged=False
                    ))

        elif dept == "finance":
            # Finance standard: SAP, Slack
            for name in ["sap", "slack"]:
                if name in catalog_map:
                    aid = catalog_map[name]["id"]
                    if aid not in [p.application_id for p in planned_apps]:
                        planned_apps.append(PlannedApplication(
                            application_id=aid,
                            reason="Standard Finance department entitlement",
                            is_privileged=False
                        ))

        elif dept == "engineering":
            # Engineering standard: GitHub, Jira, Slack
            for name in ["github", "jira", "slack"]:
                if name in catalog_map:
                    aid = catalog_map[name]["id"]
                    if aid not in [p.application_id for p in planned_apps]:
                        planned_apps.append(PlannedApplication(
                            application_id=aid,
                            reason="Standard Engineering department entitlement",
                            is_privileged=False
                        ))

    create_ticket = len(planned_apps) > 0 or create_legacy
    return PlanOutput(
        applications=planned_apps,
        create_legacy_hr=create_legacy,
        create_ticket=create_ticket,
        rationale="Plan constructed from enterprise policy rules and explicit user requests."
    )


def generate_execution_plan(
    request: str,
    employee: Optional[Dict[str, Any]],
    policies: List[Dict[str, Any]],
    catalog: List[Dict[str, Any]],
    existing_access: List[Dict[str, Any]]
) -> PlanOutput:
    """
    Generate an enterprise execution plan using Gemini with context engineering,
    falling back seamlessly to rule-based planning if needed.
    """
    client = get_genai_client()

    policies_text = "\n\n".join([f"### {p.get('title', p.get('id', 'Policy'))}\n{p.get('text', '')}" for p in policies])
    catalog_json = json.dumps([{"id": a["id"], "name": a["name"], "sensitive": a.get("sensitive", 0)} for a in catalog], indent=2)
    existing_json = json.dumps([{"id": a["id"], "name": a.get("name", "")} for a in existing_access], indent=2)
    employee_json = json.dumps(employee if employee else {}, indent=2)

    prompt = PLANNER_USER_PROMPT.format(
        request=request,
        employee_json=employee_json,
        policies_text=policies_text or "No specific policy retrieved.",
        catalog_json=catalog_json,
        existing_access_json=existing_json
    )

    if client:
        # Try primary supported models
        for model_name in ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        {"role": "user", "parts": [{"text": f"{PLANNER_SYSTEM_PROMPT}\n\n{prompt}"}]}
                    ]
                )
                raw_text = response.text.strip()
                # Clean markdown code blocks
                if "```" in raw_text:
                    raw_text = re.sub(r"```(?:json)?", "", raw_text).replace("```", "").strip()

                parsed_json = json.loads(raw_text)
                return PlanOutput.model_validate(parsed_json)
            except Exception as e:
                print(f"[Planner Warning] Model {model_name} error: {e}. Trying fallback or next model.")
                continue

    # Fallback to deterministic rule-based plan
    return heuristic_fallback_plan(request, employee, catalog, existing_access)


if __name__ == "__main__":
    test_plan = heuristic_fallback_plan(
        request="Onboard Sarah Thomas as a Sales employee and update legacy HR",
        employee={"id": "emp_001", "name": "Sarah Thomas", "department": "Sales", "role": "Account Executive"},
        catalog=[
            {"id": "app_salesforce", "name": "Salesforce", "sensitive": 0},
            {"id": "app_slack", "name": "Slack", "sensitive": 0},
            {"id": "app_jira", "name": "Jira", "sensitive": 0},
            {"id": "app_gong", "name": "Gong", "sensitive": 0},
        ],
        existing_access=[{"id": "app_slack", "name": "Slack"}]
    )
    print("Planned applications:", test_plan.applications)
    print("Create legacy HR:", test_plan.create_legacy_hr)

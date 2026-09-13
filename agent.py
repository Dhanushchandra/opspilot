import os
import json
import time
import requests

from dotenv import load_dotenv
from google import genai

from rag import search_knowledge
from tools import run_tool
from guardrails import check_access_guardrail


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.5-flash-lite"

BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# EMPLOYEE LOOKUP
# =========================================================

def find_employee(request: str) -> dict:
    """Find the employee mentioned in the request."""

    response = requests.get(
        f"{BASE_URL}/api/employees"
    )

    response.raise_for_status()

    employees = response.json()

    request_lower = request.lower()

    for employee in employees:

        if employee["name"].lower() in request_lower:
            return employee

    raise ValueError(
        "Employee could not be identified."
    )


# =========================================================
# GENERATE PLAN
# =========================================================

def generate_plan(
    request: str,
    employee: dict,
    policy: str,
    existing_access
) -> dict:

    prompt = f"""
You are OpsPilot, an enterprise IT operations agent.

USER REQUEST:
{request}

EMPLOYEE:
{json.dumps(employee, indent=2)}

ENTERPRISE POLICY:
{policy}

EXISTING ACCESS:
{json.dumps(existing_access, indent=2)}

Determine which applications the employee should receive.

Return ONLY valid JSON:

{{
    "applications": [
        {{
            "application_id": "app_example",
            "reason": "Why this application is required"
        }}
    ],
    "create_ticket": true
}}

Rules:

1. Follow enterprise policy.
2. Do not invent application IDs.
3. Do not remove existing access.
4. Do not include applications the employee already has.
5. Include only applications required by policy.
6. Privileged applications must not be granted without approval.
"""

    response = None

    # Retry transient Gemini failures.
    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            break

        except Exception as error:

            if attempt == 2:
                raise

            wait_time = 2 ** attempt

            print(
                "    Gemini request failed."
            )

            print(
                f"    Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    text = response.text.strip()

    # Remove Markdown fences.
    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        print(
            "\nGemini returned invalid JSON:"
        )

        print(text)

        raise


# =========================================================
# MAIN EXECUTION
# =========================================================

def execute(request: str) -> dict:

    print("\n" + "=" * 60)
    print("OPSPILOT EXECUTION")
    print("=" * 60)

    # -----------------------------------------------------
    # 1. FIND EMPLOYEE
    # -----------------------------------------------------

    print("\n[1] Finding employee...")

    employee = find_employee(request)

    print(
        f"    {employee['name']} | "
        f"{employee['department']} | "
        f"{employee['role']}"
    )

    # -----------------------------------------------------
    # 2. RETRIEVE POLICY
    # -----------------------------------------------------

    print("\n[2] Retrieving policy...")

    policy_results = search_knowledge(
        f"""
        Employee role: {employee['role']}
        Department: {employee['department']}

        What applications should this employee receive?

        What approvals are required?
        """,
        top_k=3
    )

    policy = "\n\n".join(
        policy_results["documents"][0]
    )

    print(
        "    Enterprise context retrieved."
    )

    # -----------------------------------------------------
    # 3. GET EXISTING ACCESS
    # -----------------------------------------------------

    print("\n[3] Checking existing access...")

    existing_access = run_tool(
        "get_employee_access",
        {
            "employee_id": employee["id"]
        }
    )

    print(
        "    Existing access retrieved."
    )

    # -----------------------------------------------------
    # Extract application IDs
    # -----------------------------------------------------

    existing_application_ids = set()

    if isinstance(existing_access, list):

        for application in existing_access:

            if isinstance(application, dict):

                application_id = application.get(
                    "id"
                )

                if application_id:

                    existing_application_ids.add(
                        application_id
                    )

    # -----------------------------------------------------
    # 4. GENERATE PLAN
    # -----------------------------------------------------

    print(
        "\n[4] Generating execution plan..."
    )

    plan = generate_plan(
        request=request,
        employee=employee,
        policy=policy,
        existing_access=existing_access
    )

    print("\n    Proposed actions:")

    for application in plan.get(
        "applications",
        []
    ):

        print(
            f"    - {application['application_id']}: "
            f"{application['reason']}"
        )

    # -----------------------------------------------------
    # 5. EXECUTE APPLICATION ACTIONS
    # -----------------------------------------------------

    print(
        "\n[5] Executing actions..."
    )

    results = []

    for application in plan.get(
        "applications",
        []
    ):

        application_id = application[
            "application_id"
        ]

        # -------------------------------------------------
        # DUPLICATE ACCESS PROTECTION
        # -------------------------------------------------

        if application_id in existing_application_ids:

            print(
                f"    SKIPPED {application_id}: "
                "access already exists."
            )

            results.append({
                "application": application_id,
                "status": "already_granted"
            })

            continue

        # -------------------------------------------------
        # GUARDRAIL
        # -------------------------------------------------

        guardrail = check_access_guardrail(
            application_id
        )

        if not guardrail["allowed"]:

            print(
                f"    BLOCKED {application_id}: "
                f"{guardrail['reason']}"
            )

            try:

                approval = run_tool(
                    "request_approval",
                    {
                        "employee_id": employee["id"],
                        "application_id": application_id
                    }
                )

                results.append({
                    "application": application_id,
                    "status": "approval_required",
                    "approval": approval
                })

            except Exception as error:

                results.append({
                    "application": application_id,
                    "status": "approval_request_failed",
                    "error": str(error)
                })

            continue

        # -------------------------------------------------
        # GRANT ACCESS
        # -------------------------------------------------

        try:

            access_result = run_tool(
                "grant_access",
                {
                    "employee_id": employee["id"],
                    "application_id": application_id
                }
            )

            print(
                f"    Granted: {application_id}"
            )

            results.append({
                "application": application_id,
                "status": "granted",
                "result": access_result
            })

        except Exception as error:

            print(
                f"    FAILED {application_id}: "
                f"{error}"
            )

            results.append({
                "application": application_id,
                "status": "failed",
                "error": str(error)
            })

    # -----------------------------------------------------
    # 6. CREATE IT TICKET
    # -----------------------------------------------------

    if plan.get(
        "create_ticket",
        False
    ):

        print(
            "\n[6] Creating IT ticket..."
        )

        try:

            ticket = run_tool(
                "create_ticket",
                {
                    "employee_id": employee["id"],
                    "title": (
                        f"Onboarding - "
                        f"{employee['name']}"
                    ),
                    "description": request
                }
            )

            print(
                "    Ticket created."
            )

            results.append({
                "ticket": ticket
            })

        except Exception as error:

            print(
                f"    Ticket creation failed: "
                f"{error}"
            )

            results.append({
                "ticket": {
                    "status": "failed",
                    "error": str(error)
                }
            })

    # -----------------------------------------------------
    # 7. COMPLETE
    # -----------------------------------------------------

    print(
        "\n[7] Execution complete."
    )

    return {
        "employee": employee,
        "results": results
    }


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    request = (
        "Onboard Sarah Thomas as a Sales employee. "
        "Give her the applications required for her role "
        "and create her IT ticket."
    )

    result = execute(request)

    print(
        "\n" + "=" * 60
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 60
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
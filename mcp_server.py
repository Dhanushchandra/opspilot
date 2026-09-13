import requests
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("OpsPilot Enterprise Tools")

BASE_URL = "http://127.0.0.1:8000"


@mcp.tool()
def get_employee(employee_id: str) -> dict:
    """Get employee information from the HR system."""
    response = requests.get(
        f"{BASE_URL}/api/employees/{employee_id}"
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def get_employee_access(employee_id: str) -> list:
    """Get applications currently assigned to an employee."""
    response = requests.get(
        f"{BASE_URL}/api/employees/{employee_id}/access"
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def get_applications() -> list:
    """Get all applications available in the enterprise."""
    response = requests.get(
        f"{BASE_URL}/api/applications"
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def grant_access(
    employee_id: str,
    application_id: str
) -> dict:
    """Grant an application to an employee."""
    response = requests.post(
        f"{BASE_URL}/api/employees/{employee_id}/access",
        json={
            "application_id": application_id
        }
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def create_ticket(
    employee_id: str,
    title: str,
    description: str
) -> dict:
    """Create an ITSM ticket for an employee."""
    response = requests.post(
        f"{BASE_URL}/api/tickets",
        json={
            "employee_id": employee_id,
            "title": title,
            "description": description
        }
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def request_approval(
    employee_id: str,
    application_id: str
) -> dict:
    """Request approval for privileged application access."""
    response = requests.post(
        f"{BASE_URL}/api/approvals",
        json={
            "employee_id": employee_id,
            "application_id": application_id
        }
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def check_approval(
    approval_id: str
) -> dict:
    """Check the status of an access approval."""
    response = requests.get(
        f"{BASE_URL}/api/approvals/{approval_id}"
    )

    response.raise_for_status()

    return response.json()


@mcp.tool()
def verify_access(
    employee_id: str,
    application_id: str
) -> dict:
    """Verify that an employee has application access."""

    access = get_employee_access(employee_id)

    for application in access:
        if application["id"] == application_id:
            return {
                "verified": True,
                "application": application["name"]
            }

    return {
        "verified": False,
        "application_id": application_id
    }


if __name__ == "__main__":
    mcp.run()
"""
OpsPilot Enterprise MCP Server.
Exposes enterprise operations as MCP tools over stdio protocol.
"""

import sys
import logging
from typing import Dict, Any, List
from mcp.server.mcpserver import MCPServer

from integrations import database
from rpa.legacy_automation import create_employee_in_legacy_system, remove_employee_from_legacy_system

# Configure logging to stderr only so stdout remains clean for MCP JSON-RPC protocol
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_server")

mcp_server = MCPServer("OpsPilot Enterprise Operations Server")


@mcp_server.tool()
def get_employee(employee_id: str) -> Dict[str, Any]:
    """Retrieve employee profile by ID (name, department, role, email)."""
    logger.info(f"Tool call: get_employee({employee_id})")
    emp = database.get_employee_by_id(employee_id)
    if not emp:
        return {"error": f"Employee '{employee_id}' not found."}
    return emp


@mcp_server.tool()
def get_employee_access(employee_id: str) -> List[Dict[str, Any]]:
    """Get list of applications currently assigned to an employee."""
    logger.info(f"Tool call: get_employee_access({employee_id})")
    return database.get_employee_access(employee_id)


@mcp_server.tool()
def get_applications() -> List[Dict[str, Any]]:
    """Retrieve the complete catalog of enterprise applications."""
    logger.info("Tool call: get_applications()")
    return database.get_all_applications()


@mcp_server.tool()
def grant_access(employee_id: str, application_id: str) -> Dict[str, Any]:
    """Grant an application to an employee. Prevents duplicate grants."""
    logger.info(f"Tool call: grant_access({employee_id}, {application_id})")
    try:
        return database.grant_access(employee_id, application_id)
    except Exception as e:
        logger.error(f"Error in grant_access: {e}")
        return {"error": str(e), "status": "failed"}


@mcp_server.tool()
def revoke_access(employee_id: str, application_id: str) -> Dict[str, Any]:
    """Revoke an application entitlement from an employee."""
    logger.info(f"Tool call: revoke_access({employee_id}, {application_id})")
    revoked = database.revoke_access(employee_id, application_id)
    return {"revoked": revoked, "employee_id": employee_id, "application_id": application_id}


@mcp_server.tool()
def verify_access(employee_id: str, application_id: str) -> Dict[str, Any]:
    """Verify that an employee has active access to an application."""
    logger.info(f"Tool call: verify_access({employee_id}, {application_id})")
    return database.verify_access(employee_id, application_id)


@mcp_server.tool()
def create_ticket(employee_id: str, title: str, description: str, actions_performed: str = "") -> Dict[str, Any]:
    """Create an ITSM ticket documenting operations performed."""
    logger.info(f"Tool call: create_ticket({employee_id}, {title})")
    return database.create_ticket(employee_id, title, description, actions_performed)


@mcp_server.tool()
def update_ticket_status(ticket_id: str, status: str, resolution_notes: str = "") -> Dict[str, Any]:
    """Update status of an ITSM ticket (OPEN, IN_PROGRESS, RESOLVED, CLOSED)."""
    logger.info(f"Tool call: update_ticket_status({ticket_id}, {status})")
    ticket = database.update_ticket_status(ticket_id, status, resolution_notes)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}
    return ticket


@mcp_server.tool()
def request_approval(employee_id: str, application_id: str, comments: str = "") -> Dict[str, Any]:
    """Submit an authorization request for privileged application access."""
    logger.info(f"Tool call: request_approval({employee_id}, {application_id})")
    return database.request_approval(employee_id, application_id, comments)


@mcp_server.tool()
def check_approval(approval_id: str) -> Dict[str, Any]:
    """Check the approval status of a privileged access request (PENDING, APPROVED, REJECTED)."""
    logger.info(f"Tool call: check_approval({approval_id})")
    approval = database.check_approval(approval_id)
    if not approval:
        return {"error": f"Approval '{approval_id}' not found."}
    return approval


@mcp_server.tool()
def create_employee_legacy(employee_id: str, name: str, department: str, role: str) -> Dict[str, Any]:
    """Create an employee record in the legacy HR system via Playwright browser automation."""
    logger.info(f"Tool call: create_employee_legacy({employee_id}, {name})")
    return create_employee_in_legacy_system(
        employee_id=employee_id,
        name=name,
        department=department,
        role=role
    )


@mcp_server.tool()
def remove_employee_legacy(employee_id: str) -> Dict[str, Any]:
    """Remove an employee record from the legacy HR system via Playwright browser automation."""
    logger.info(f"Tool call: remove_employee_legacy({employee_id})")
    return remove_employee_from_legacy_system(employee_id=employee_id)


@mcp_server.tool()
def delete_employee_hr(employee_id: str) -> Dict[str, Any]:
    """Delete an employee and their entitlements from the central HR enterprise directory."""
    logger.info(f"Tool call: delete_employee_hr({employee_id})")
    deleted = database.delete_employee(employee_id)
    return {"deleted": deleted, "employee_id": employee_id}


if __name__ == "__main__":
    mcp_server.run()

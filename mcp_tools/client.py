"""
MCP Client and Unified Tool Execution Engine for OpsPilot.
Handles execution, latency tracking, error handling, and MCP tool mapping.
"""

import time
import json
from typing import Dict, Any, Optional

from integrations import database
from rpa.legacy_automation import create_employee_in_legacy_system

# In-process tool registry matching MCP server tools
TOOL_REGISTRY = {
    "get_employee": lambda args: database.get_employee_by_id(args["employee_id"]),
    "get_employee_access": lambda args: database.get_employee_access(args["employee_id"]),
    "get_applications": lambda args: database.get_all_applications(),
    "grant_access": lambda args: database.grant_access(args["employee_id"], args["application_id"]),
    "revoke_access": lambda args: database.revoke_access(args["employee_id"], args["application_id"]),
    "verify_access": lambda args: database.verify_access(args["employee_id"], args["application_id"]),
    "create_ticket": lambda args: database.create_ticket(
        args["employee_id"],
        args["title"],
        args.get("description", ""),
        args.get("actions_performed", "")
    ),
    "update_ticket_status": lambda args: database.update_ticket_status(
        args["ticket_id"],
        args["status"],
        args.get("resolution_notes", "")
    ),
    "request_approval": lambda args: database.request_approval(
        args["employee_id"],
        args["application_id"],
        args.get("comments", "")
    ),
    "check_approval": lambda args: database.check_approval(args["approval_id"]),
    "create_employee_legacy": lambda args: create_employee_in_legacy_system(
        args["employee_id"],
        args["name"],
        args["department"],
        args["role"]
    )
}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an enterprise tool with precise latency tracking and error wrapping.
    Returns:
    {
        "tool": tool_name,
        "arguments": arguments,
        "result": result_data,
        "status": "SUCCESS" | "FAILED",
        "latency_ms": elapsed_time_in_ms,
        "error": error_message_or_None
    }
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": None,
            "status": "FAILED",
            "latency_ms": 0.0,
            "error": f"Tool '{tool_name}' is not registered."
        }

    start_time = time.perf_counter()
    try:
        fn = TOOL_REGISTRY[tool_name]
        result = fn(arguments)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "status": "SUCCESS",
            "latency_ms": latency_ms,
            "error": None
        }
    except Exception as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": None,
            "status": "FAILED",
            "latency_ms": latency_ms,
            "error": str(e)
        }


if __name__ == "__main__":
    test_run = execute_tool("get_employee", {"employee_id": "emp_001"})
    print("Tool test execution:", test_run)

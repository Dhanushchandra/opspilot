"""
Structured State Definition for OpsPilot LangGraph Agent.
"""

from typing import TypedDict, List, Dict, Any, Optional


class StepTrace(TypedDict):
    step: str
    status: str  # 'RUNNING', 'SUCCESS', 'SKIPPED', 'WARNING', 'BLOCKED', 'FAILED'
    message: str
    details: Optional[Dict[str, Any]]
    timestamp: str


class FunctionCallRecord(TypedDict):
    timestamp: str
    node: str
    function_name: str
    module: str
    input_params: Dict[str, Any]
    guardrail_verdict: Optional[str]
    output_summary: str
    latency_ms: float


class OpsPilotState(TypedDict):
    # User Request Context
    request: str
    request_id: str
    auto_approve: bool

    # Security & Injection Check
    injection_flagged: bool

    # Employee Identification
    employee: Optional[Dict[str, Any]]
    identity_status: str  # 'RESOLVED', 'AMBIGUOUS', 'NOT_FOUND'
    identity_message: str

    # Enterprise Context & Current State
    policies: List[Dict[str, Any]]
    existing_access: List[Dict[str, Any]]
    catalog: List[Dict[str, Any]]
    legacy_required: bool

    # Planning & Validation
    raw_plan: Dict[str, Any]
    validated_actions: List[Dict[str, Any]]
    skipped_actions: List[Dict[str, Any]]
    rejected_actions: List[Dict[str, Any]]

    # Approvals & Guardrails
    pending_approvals: List[Dict[str, Any]]
    approved_actions: List[Dict[str, Any]]

    # Execution & Verification
    tool_executions: List[Dict[str, Any]]
    verification_results: List[Dict[str, Any]]

    # Ticketing
    ticket: Optional[Dict[str, Any]]

    # Deep Telemetry & Function Call Stack
    function_call_stack: List[FunctionCallRecord]

    # Final Output & Lifecycle
    final_summary: str
    status: str  # 'COMPLETED', 'PENDING_APPROVAL', 'CLARIFICATION_REQUIRED', 'BLOCKED_GUARDRAIL', 'FAILED'
    trace: List[StepTrace]
    error: Optional[str]

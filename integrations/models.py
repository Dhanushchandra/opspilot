"""
Pydantic data models for OpsPilot Enterprise Systems.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EmployeeModel(BaseModel):
    id: str
    name: str
    department: str
    role: str
    email: Optional[str] = None


class EmployeeCreateRequest(BaseModel):
    id: str
    name: str
    department: str
    role: str
    email: Optional[str] = None


class ApplicationModel(BaseModel):
    id: str
    name: str
    sensitive: int = 0
    description: Optional[str] = None


class ApplicationCreateRequest(BaseModel):
    id: str
    name: str
    sensitive: int = 0
    description: Optional[str] = None


class AccessGrantRequest(BaseModel):
    application_id: str


class TicketRequest(BaseModel):
    employee_id: str
    title: str
    description: str
    actions_performed: Optional[str] = ""


class ApprovalRequestModel(BaseModel):
    employee_id: str
    application_id: str
    comments: Optional[str] = ""


class ApprovalReviewRequest(BaseModel):
    status: str = Field(description="APPROVED or REJECTED")
    comments: Optional[str] = ""


class ToolCallTrace(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    result: Any
    status: str
    latency_ms: float
    error: Optional[str] = None

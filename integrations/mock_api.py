"""
FastAPI REST API simulating enterprise HR, Application Access, ITSM, and Approval Systems.
Backed by SQLite database in integrations.database.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional

from integrations import database
from integrations.models import (
    EmployeeModel,
    EmployeeCreateRequest,
    ApplicationModel,
    ApplicationCreateRequest,
    AccessGrantRequest,
    TicketRequest,
    ApprovalRequestModel,
    ApprovalReviewRequest
)

app = FastAPI(
    title="OpsPilot Enterprise Integration API",
    description="Simulated multi-system IT operations API for HR, IAM, ITSM, and Governance.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Ensure database tables and initial seed data are initialized."""
    database.init_db(force_reset=False)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "OpsPilot Mock Enterprise API"}


@app.post("/api/admin/reset")
def reset_database():
    """Reset the database to initial clean seed state."""
    database.init_db(force_reset=True)
    return {"status": "success", "message": "Database reset to initial seed data."}


# -------------------------------------------------------------
# HR Endpoints
# -------------------------------------------------------------

@app.get("/api/employees", response_model=List[Dict[str, Any]])
def list_employees():
    return database.get_all_employees()


@app.get("/api/employees/search")
def search_employees(q: str):
    return database.find_employees_by_name(q)


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: str):
    emp = database.get_employee_by_id(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return emp


@app.post("/api/employees", status_code=status.HTTP_201_CREATED)
def create_employee(req: EmployeeCreateRequest):
    try:
        return database.create_employee(
            employee_id=req.id,
            name=req.name,
            department=req.department,
            role=req.role,
            email=req.email
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: str):
    deleted = database.delete_employee(employee_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return {"status": "deleted", "id": employee_id}


# -------------------------------------------------------------
# Application Catalog & Access Endpoints
# -------------------------------------------------------------

@app.get("/api/applications", response_model=List[Dict[str, Any]])
def list_applications():
    return database.get_all_applications()


@app.get("/api/applications/{app_id}")
def get_application(app_id: str):
    app_obj = database.get_application_by_id(app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return app_obj


@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
def create_application(req: ApplicationCreateRequest):
    try:
        return database.create_application(
            app_id=req.id,
            name=req.name,
            sensitive=req.sensitive,
            description=req.description or ""
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/employees/{employee_id}/access")
def get_employee_access(employee_id: str):
    emp = database.get_employee_by_id(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return database.get_employee_access(employee_id)


@app.post("/api/employees/{employee_id}/access")
def grant_employee_access(employee_id: str, req: AccessGrantRequest):
    try:
        result = database.grant_access(employee_id, req.application_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/employees/{employee_id}/access/{application_id}")
def revoke_employee_access(employee_id: str, application_id: str):
    revoked = database.revoke_access(employee_id, application_id)
    return {"status": "revoked" if revoked else "not_found", "employee_id": employee_id, "application_id": application_id}


@app.get("/api/employees/{employee_id}/access/{application_id}/verify")
def verify_employee_access(employee_id: str, application_id: str):
    return database.verify_access(employee_id, application_id)


# -------------------------------------------------------------
# ITSM Endpoints
# -------------------------------------------------------------

@app.get("/api/tickets")
def list_tickets():
    return database.get_all_tickets()


@app.post("/api/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(req: TicketRequest):
    emp = database.get_employee_by_id(req.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{req.employee_id}' not found.")
    return database.create_ticket(
        employee_id=req.employee_id,
        title=req.title,
        description=req.description,
        actions_performed=req.actions_performed or ""
    )


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = database.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    return ticket


# -------------------------------------------------------------
# Approval Endpoints
# -------------------------------------------------------------

@app.get("/api/approvals")
def list_approvals():
    return database.get_all_approvals()


@app.post("/api/approvals", status_code=status.HTTP_201_CREATED)
def request_approval(req: ApprovalRequestModel):
    emp = database.get_employee_by_id(req.employee_id)
    app_obj = database.get_application_by_id(req.application_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{req.employee_id}' not found.")
    if not app_obj:
        raise HTTPException(status_code=404, detail=f"Application '{req.application_id}' not found.")

    return database.request_approval(
        employee_id=req.employee_id,
        application_id=req.application_id,
        comments=req.comments or ""
    )


@app.get("/api/approvals/{approval_id}")
def check_approval(approval_id: str):
    approval = database.check_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval request '{approval_id}' not found.")
    return approval


@app.post("/api/approvals/{approval_id}/approve")
def approve_request(approval_id: str, comments: Optional[str] = "Approved via OpsPilot workflow"):
    updated = database.update_approval_status(approval_id, "APPROVED", comments)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found.")
    return updated


@app.post("/api/approvals/{approval_id}/reject")
def reject_request(approval_id: str, comments: Optional[str] = "Rejected by reviewer"):
    updated = database.update_approval_status(approval_id, "REJECTED", comments)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found.")
    return updated


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("integrations.mock_api:app", host="127.0.0.1", port=8000, reload=True)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
import uuid

app = FastAPI(title="OpsPilot Mock Enterprise API")

DB = "opspilot.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS employees (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS applications (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        sensitive INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS employee_access (
        employee_id TEXT,
        application_id TEXT,
        PRIMARY KEY (employee_id, application_id)
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        employee_id TEXT,
        title TEXT,
        description TEXT,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        employee_id TEXT,
        application_id TEXT,
        status TEXT
    );
    """)

    # Seed employees
    employees = [
        ("emp_001", "Sarah Thomas", "Sales", "Account Executive"),
        ("emp_002", "Rahul Sharma", "Engineering", "Software Engineer"),
        ("emp_003", "Priya Nair", "Finance", "Financial Analyst"),
    ]

    conn.executemany(
        "INSERT OR IGNORE INTO employees VALUES (?, ?, ?, ?)",
        employees
    )

    # Seed applications
    applications = [
        ("app_salesforce", "Salesforce", 0),
        ("app_slack", "Slack", 0),
        ("app_jira", "Jira", 0),
        ("app_github", "GitHub", 0),
        ("app_sap", "SAP", 0),
        ("app_finance_admin", "Finance Admin Portal", 1),
        ("app_sales_admin", "Sales Admin Portal", 1),
    ]

    conn.executemany(
        "INSERT OR IGNORE INTO applications VALUES (?, ?, ?)",
        applications
    )

    # Sarah already has Slack
    conn.execute(
        """
        INSERT OR IGNORE INTO employee_access
        VALUES (?, ?)
        """,
        ("emp_001", "app_slack")
    )

    conn.commit()
    conn.close()


class TicketRequest(BaseModel):
    employee_id: str
    title: str
    description: str


class AccessRequest(BaseModel):
    application_id: str


class ApprovalRequest(BaseModel):
    employee_id: str
    application_id: str


@app.on_event("startup")
def startup():
    init_db()


# -------------------------
# HR API
# -------------------------

@app.get("/api/employees")
def get_employees():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM employees"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: str):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM employees WHERE id = ?",
        (employee_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Employee not found")

    return dict(row)


# -------------------------
# Application API
# -------------------------

@app.get("/api/applications")
def get_applications():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applications"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/api/employees/{employee_id}/access")
def get_access(employee_id: str):
    conn = get_db()

    rows = conn.execute("""
        SELECT a.id, a.name, a.sensitive
        FROM applications a
        JOIN employee_access ea
        ON a.id = ea.application_id
        WHERE ea.employee_id = ?
    """, (employee_id,)).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/employees/{employee_id}/access")
def grant_access(
    employee_id: str,
    request: AccessRequest
):
    conn = get_db()

    employee = conn.execute(
        "SELECT * FROM employees WHERE id = ?",
        (employee_id,)
    ).fetchone()

    application = conn.execute(
        "SELECT * FROM applications WHERE id = ?",
        (request.application_id,)
    ).fetchone()

    if not employee:
        raise HTTPException(404, "Employee not found")

    if not application:
        raise HTTPException(404, "Application not found")

    existing = conn.execute("""
        SELECT * FROM employee_access
        WHERE employee_id = ?
        AND application_id = ?
    """, (employee_id, request.application_id)).fetchone()

    if existing:
        conn.close()
        return {
            "status": "already_granted",
            "message": "Employee already has this access"
        }

    conn.execute("""
        INSERT INTO employee_access
        VALUES (?, ?)
    """, (employee_id, request.application_id))

    conn.commit()
    conn.close()

    return {
        "status": "granted",
        "employee_id": employee_id,
        "application": application["name"]
    }


# -------------------------
# ITSM API
# -------------------------

@app.post("/api/tickets")
def create_ticket(request: TicketRequest):
    ticket_id = "INC-" + str(uuid.uuid4())[:8]

    conn = get_db()

    conn.execute("""
        INSERT INTO tickets
        VALUES (?, ?, ?, ?, ?)
    """, (
        ticket_id,
        request.employee_id,
        request.title,
        request.description,
        "OPEN"
    ))

    conn.commit()
    conn.close()

    return {
        "ticket_id": ticket_id,
        "status": "OPEN",
        "message": "Ticket created successfully"
    }


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM tickets WHERE id = ?",
        (ticket_id,)
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(404, "Ticket not found")

    return dict(row)


# -------------------------
# Approval API
# -------------------------

@app.post("/api/approvals")
def request_approval(request: ApprovalRequest):
    approval_id = "APR-" + str(uuid.uuid4())[:8]

    conn = get_db()

    conn.execute("""
        INSERT INTO approvals
        VALUES (?, ?, ?, ?)
    """, (
        approval_id,
        request.employee_id,
        request.application_id,
        "PENDING"
    ))

    conn.commit()
    conn.close()

    return {
        "approval_id": approval_id,
        "status": "PENDING"
    }


@app.get("/api/approvals/{approval_id}")
def check_approval(approval_id: str):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM approvals WHERE id = ?",
        (approval_id,)
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(404, "Approval not found")

    return dict(row)


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: str):
    conn = get_db()

    conn.execute("""
        UPDATE approvals
        SET status = 'APPROVED'
        WHERE id = ?
    """, (approval_id,))

    conn.commit()

    row = conn.execute(
        "SELECT * FROM approvals WHERE id = ?",
        (approval_id,)
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(404, "Approval not found")

    return dict(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "integrations.mock_api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
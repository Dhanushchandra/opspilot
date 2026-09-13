"""
Database management for OpsPilot Enterprise Systems.
Simulates HR, Application Access, ITSM, and Approval databases via SQLite.
"""

import sqlite3
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("opspilot.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to the SQLite database with row factory and WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(force_reset: bool = False):
    """Initialize database tables and seed initial data if empty or requested."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if force_reset:
        cursor.executescript("""
            DROP TABLE IF EXISTS execution_logs;
            DROP TABLE IF EXISTS approvals;
            DROP TABLE IF EXISTS tickets;
            DROP TABLE IF EXISTS employee_access;
            DROP TABLE IF EXISTS applications;
            DROP TABLE IF EXISTS employees;
        """)

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sensitive INTEGER DEFAULT 0,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS employee_access (
            employee_id TEXT NOT NULL,
            application_id TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            PRIMARY KEY (employee_id, application_id),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL,
            actions_performed TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            application_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            requested_at TEXT NOT NULL,
            reviewed_at TEXT,
            comments TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS execution_logs (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            step TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            timestamp TEXT NOT NULL
        );
    """)

    # Check if employees already exist
    cursor.execute("SELECT COUNT(*) FROM employees;")
    count = cursor.fetchone()[0]

    if count == 0 or force_reset:
        now = datetime.datetime.utcnow().isoformat()

        # Seed Employees
        # Note: Alex Rivera & Alex Johnson allow testing ambiguous name resolution ("Alex")
        employees = [
            ("emp_001", "Sarah Thomas", "Sales", "Account Executive", "sarah.thomas@enterprise.com"),
            ("emp_002", "Rahul Sharma", "Engineering", "Software Engineer", "rahul.sharma@enterprise.com"),
            ("emp_003", "Priya Nair", "Finance", "Financial Analyst", "priya.nair@enterprise.com"),
            ("emp_004", "Alex Johnson", "Sales", "Sales Representative", "alex.johnson@enterprise.com"),
            ("emp_005", "Alex Rivera", "Engineering", "DevOps Engineer", "alex.rivera@enterprise.com"),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO employees (id, name, department, role, email) VALUES (?, ?, ?, ?, ?);",
            employees
        )

        # Seed Applications
        applications = [
            ("app_salesforce", "Salesforce", 0, "Enterprise CRM for Sales"),
            ("app_slack", "Slack", 0, "Enterprise Team Chat & Collaboration"),
            ("app_jira", "Jira", 0, "Issue Tracking & Project Management"),
            ("app_gong", "Gong", 0, "Revenue Intelligence & Sales Call Analysis"),
            ("app_github", "GitHub", 0, "Source Code Repository & Version Control"),
            ("app_sap", "SAP", 0, "Enterprise Resource Planning for Finance"),
            ("app_sales_admin", "Sales Admin Portal", 1, "Privileged administrative console for Sales"),
            ("app_finance_admin", "Finance Admin Portal", 1, "Privileged administrative console for Finance"),
        ]
        cursor.executemany(
            "INSERT OR REPLACE INTO applications (id, name, sensitive, description) VALUES (?, ?, ?, ?);",
            applications
        )

        # Sarah Thomas already has Slack to test duplicate access prevention
        cursor.execute(
            "INSERT OR REPLACE INTO employee_access (employee_id, application_id, granted_at) VALUES (?, ?, ?);",
            ("emp_001", "app_slack", now)
        )

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# Employee CRUD
# -------------------------------------------------------------

def get_all_employees() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM employees ORDER BY name ASC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_employee_by_id(employee_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM employees WHERE id = ?;", (employee_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_employees_by_name(name_query: str) -> List[Dict[str, Any]]:
    """Search employees by exact match or substring match (case-insensitive)."""
    conn = get_db_connection()
    query_clean = name_query.strip().lower()
    all_emps = conn.execute("SELECT * FROM employees;").fetchall()
    conn.close()

    exact_matches = []
    partial_matches = []

    for r in all_emps:
        emp = dict(r)
        emp_name_lower = emp["name"].lower()
        if emp_name_lower == query_clean:
            exact_matches.append(emp)
        elif query_clean in emp_name_lower or any(part in emp_name_lower for part in query_clean.split()):
            partial_matches.append(emp)

    return exact_matches if exact_matches else partial_matches


def create_employee(employee_id: str, name: str, department: str, role: str, email: Optional[str] = None) -> Dict[str, Any]:
    conn = get_db_connection()
    if not email:
        email = f"{name.lower().replace(' ', '.')}@enterprise.com"
    conn.execute(
        "INSERT INTO employees (id, name, department, role, email) VALUES (?, ?, ?, ?, ?);",
        (employee_id, name, department, role, email)
    )
    conn.commit()
    conn.close()
    return {"id": employee_id, "name": name, "department": department, "role": role, "email": email}


def delete_employee(employee_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE id = ?;", (employee_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# -------------------------------------------------------------
# Application CRUD
# -------------------------------------------------------------

def get_all_applications() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM applications ORDER BY name ASC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_application_by_id(app_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM applications WHERE id = ?;", (app_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_application(app_id: str, name: str, sensitive: int = 0, description: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO applications (id, name, sensitive, description) VALUES (?, ?, ?, ?);",
        (app_id, name, sensitive, description)
    )
    conn.commit()
    conn.close()
    return {"id": app_id, "name": name, "sensitive": sensitive, "description": description}


# -------------------------------------------------------------
# Employee Access Operations
# -------------------------------------------------------------

def get_employee_access(employee_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT a.id, a.name, a.sensitive, a.description, ea.granted_at
        FROM applications a
        JOIN employee_access ea ON a.id = ea.application_id
        WHERE ea.employee_id = ?
        ORDER BY a.name ASC;
    """, (employee_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def grant_access(employee_id: str, application_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    # Check employee and application exist
    emp = conn.execute("SELECT * FROM employees WHERE id = ?;", (employee_id,)).fetchone()
    app = conn.execute("SELECT * FROM applications WHERE id = ?;", (application_id,)).fetchone()

    if not emp:
        conn.close()
        raise ValueError(f"Employee {employee_id} not found")
    if not app:
        conn.close()
        raise ValueError(f"Application {application_id} not found")

    existing = conn.execute(
        "SELECT * FROM employee_access WHERE employee_id = ? AND application_id = ?;",
        (employee_id, application_id)
    ).fetchone()

    if existing:
        conn.close()
        return {
            "status": "already_granted",
            "message": f"Employee already has access to {app['name']}",
            "employee_id": employee_id,
            "application_id": application_id,
            "application": app["name"]
        }

    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO employee_access (employee_id, application_id, granted_at) VALUES (?, ?, ?);",
        (employee_id, application_id, now)
    )
    conn.commit()
    conn.close()

    return {
        "status": "granted",
        "employee_id": employee_id,
        "application_id": application_id,
        "application": app["name"],
        "granted_at": now
    }


def revoke_access(employee_id: str, application_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM employee_access WHERE employee_id = ? AND application_id = ?;",
        (employee_id, application_id)
    )
    conn.commit()
    revoked = cursor.rowcount > 0
    conn.close()
    return revoked


def verify_access(employee_id: str, application_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    row = conn.execute("""
        SELECT a.id, a.name, a.sensitive, ea.granted_at
        FROM applications a
        JOIN employee_access ea ON a.id = ea.application_id
        WHERE ea.employee_id = ? AND ea.application_id = ?;
    """, (employee_id, application_id)).fetchone()
    conn.close()

    if row:
        return {
            "verified": True,
            "employee_id": employee_id,
            "application_id": application_id,
            "application": row["name"],
            "granted_at": row["granted_at"]
        }
    return {
        "verified": False,
        "employee_id": employee_id,
        "application_id": application_id,
        "message": f"Access record not found for {application_id}"
    }


# -------------------------------------------------------------
# ITSM Tickets
# -------------------------------------------------------------

def create_ticket(employee_id: str, title: str, description: str, actions_performed: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    ticket_id = "INC-" + str(uuid.uuid4())[:8].upper()
    now = datetime.datetime.utcnow().isoformat()

    conn.execute(
        "INSERT INTO tickets (id, employee_id, title, description, status, created_at, actions_performed) VALUES (?, ?, ?, ?, ?, ?, ?);",
        (ticket_id, employee_id, title, description, "OPEN", now, actions_performed)
    )
    conn.commit()
    conn.close()

    return {
        "ticket_id": ticket_id,
        "employee_id": employee_id,
        "title": title,
        "description": description,
        "status": "OPEN",
        "created_at": now,
        "actions_performed": actions_performed
    }


def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?;", (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_tickets() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -------------------------------------------------------------
# Approvals
# -------------------------------------------------------------

def request_approval(employee_id: str, application_id: str, comments: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    # Check if there is already an active pending approval
    existing = conn.execute(
        "SELECT * FROM approvals WHERE employee_id = ? AND application_id = ? AND status = 'PENDING';",
        (employee_id, application_id)
    ).fetchone()

    if existing:
        conn.close()
        return dict(existing)

    approval_id = "APR-" + str(uuid.uuid4())[:8].upper()
    now = datetime.datetime.utcnow().isoformat()

    conn.execute(
        "INSERT INTO approvals (id, employee_id, application_id, status, requested_at, comments) VALUES (?, ?, ?, ?, ?, ?);",
        (approval_id, employee_id, application_id, "PENDING", now, comments)
    )
    conn.commit()
    conn.close()

    return {
        "approval_id": approval_id,
        "employee_id": employee_id,
        "application_id": application_id,
        "status": "PENDING",
        "requested_at": now,
        "comments": comments
    }


def check_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM approvals WHERE id = ?;", (approval_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_approval_status(approval_id: str, status: str, comments: str = "") -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    now = datetime.datetime.utcnow().isoformat()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE approvals SET status = ?, reviewed_at = ?, comments = ? WHERE id = ?;",
        (status.upper(), now, comments, approval_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM approvals WHERE id = ?;", (approval_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_approvals() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT ap.*, e.name as employee_name, a.name as application_name
        FROM approvals ap
        LEFT JOIN employees e ON ap.employee_id = e.id
        LEFT JOIN applications a ON ap.application_id = a.id
        ORDER BY ap.requested_at DESC;
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db(force_reset=True)
    print("Database initialized and seeded successfully.")

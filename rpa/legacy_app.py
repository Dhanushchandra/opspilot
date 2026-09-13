"""
Simulated Legacy HR Web Application (Port 8001).
Represents an un-API-fied legacy portal requiring browser automation (Playwright/RPA).
"""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any

app = FastAPI(title="OpsPilot Legacy HR System", version="1.0.0")

# In-memory legacy database pre-seeded with some initial legacy staff
legacy_employees: Dict[str, Dict[str, Any]] = {
    "emp_000": {
        "employee_id": "emp_000",
        "name": "System Administrator",
        "department": "IT Operations",
        "role": "Root Admin"
    }
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "Legacy HR System", "records": len(legacy_employees)}


@app.get("/api/legacy/employees")
def api_list_employees():
    return list(legacy_employees.values())


@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Enterprise Legacy HR Portal</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 32px; border-radius: 8px; border: 1px solid #334155; width: 340px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { font-size: 20px; margin-bottom: 20px; color: #38bdf8; text-align: center; }
            label { font-size: 13px; color: #94a3b8; display: block; margin-bottom: 6px; }
            input { width: 100%; box-sizing: border-box; padding: 10px; margin-bottom: 16px; background: #0f172a; border: 1px solid #475569; border-radius: 4px; color: #f8fafc; }
            button { width: 100%; padding: 10px; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
            button:hover { background: #0369a1; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Legacy HR Portal v3.2</h1>
            <form action="/login" method="post">
                <label for="username">Username</label>
                <input id="username" name="username" value="admin" required>
                <label for="password">Password</label>
                <input id="password" name="password" type="password" value="admin123" required>
                <button id="login" type="submit">Log In</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin123":
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Legacy HR Dashboard</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }
                .container { max-width: 600px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 8px; border: 1px solid #334155; }
                h1 { color: #38bdf8; }
                .btn { display: inline-block; padding: 10px 16px; background: #0284c7; color: white; text-decoration: none; border-radius: 4px; margin-right: 12px; font-weight: 500; }
                .btn:hover { background: #0369a1; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Legacy HR Administration Dashboard</h1>
                <p>Authenticated as Administrator. Please select an action:</p>
                <div style="margin-top: 24px;">
                    <a id="add-employee" class="btn" href="/employees/new">Add Employee Record</a>
                    <a id="employee-list" class="btn" href="/employees">View Legacy Database</a>
                </div>
            </div>
        </body>
        </html>
        """

    return """
    <h2 id="error" style="color: #ef4444; font-family: sans-serif; text-align: center; margin-top: 50px;">
        Invalid username or password
    </h2>
    """


@app.get("/employees/new", response_class=HTMLResponse)
def new_employee():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Legacy HR - Create Employee</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }
            .card { max-width: 500px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 8px; border: 1px solid #334155; }
            h1 { color: #38bdf8; font-size: 22px; margin-bottom: 20px; }
            label { font-size: 13px; color: #94a3b8; display: block; margin-bottom: 6px; }
            input { width: 100%; box-sizing: border-box; padding: 10px; margin-bottom: 16px; background: #0f172a; border: 1px solid #475569; border-radius: 4px; color: #f8fafc; }
            button { width: 100%; padding: 12px; background: #10b981; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; }
            button:hover { background: #059669; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Create Legacy Employee Record</h1>
            <form action="/employees/create" method="post">
                <label for="employee_id">Employee ID</label>
                <input id="employee_id" name="employee_id" placeholder="e.g. emp_001" required>

                <label for="name">Full Name</label>
                <input id="name" name="name" placeholder="e.g. Sarah Thomas" required>

                <label for="department">Department</label>
                <input id="department" name="department" placeholder="e.g. Sales" required>

                <label for="role">Role</label>
                <input id="role" name="role" placeholder="e.g. Account Executive" required>

                <button id="create" type="submit">Submit Employee Record</button>
            </form>
        </div>
    </body>
    </html>
    """


@app.post("/employees/create", response_class=HTMLResponse)
def create_employee(
    employee_id: str = Form(...),
    name: str = Form(...),
    department: str = Form(...),
    role: str = Form(...)
):
    legacy_employees[employee_id] = {
        "employee_id": employee_id,
        "name": name,
        "department": department,
        "role": role
    }

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Employee Created</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }}
            .card {{ max-width: 500px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 8px; border: 1px solid #334155; }}
            h1 {{ color: #10b981; font-size: 20px; }}
            p {{ font-size: 15px; color: #cbd5e1; margin: 10px 0; }}
            strong {{ color: #38bdf8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 id="success">Employee created successfully</h1>
            <p>Employee ID: <strong id="employee-id">{employee_id}</strong></p>
            <p>Name: <strong id="employee-name">{name}</strong></p>
            <p>Department: <strong id="employee-department">{department}</strong></p>
            <p>Role: <strong id="employee-role">{role}</strong></p>
            <div style="margin-top: 20px;">
                <a href="/employees" style="color: #38bdf8;">View All Records</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/employees", response_class=HTMLResponse)
def employee_list():
    rows = ""
    for emp in legacy_employees.values():
        rows += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #334155;">{emp['employee_id']}</td>
            <td style="padding: 10px; border: 1px solid #334155;">{emp['name']}</td>
            <td style="padding: 10px; border: 1px solid #334155;">{emp['department']}</td>
            <td style="padding: 10px; border: 1px solid #334155;">{emp['role']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Legacy Employee Database</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 8px; border: 1px solid #334155; }}
            h1 {{ color: #38bdf8; font-size: 22px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #0f172a; padding: 12px; text-align: left; color: #94a3b8; border: 1px solid #334155; }}
            a {{ color: #38bdf8; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Legacy HR Employee Database</h1>
            <p><a href="/employees/new">+ Add New Record</a> | <a href="/login">Dashboard</a></p>
            <table>
                <thead>
                    <tr>
                        <th>Employee ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Role</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
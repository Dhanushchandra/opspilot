"""
Unit tests for database operations in integrations.database.
"""

import pytest
from integrations import database


@pytest.fixture(autouse=True)
def setup_db():
    database.init_db(force_reset=True)
    yield


def test_seed_employees():
    employees = database.get_all_employees()
    assert len(employees) >= 5
    sarah = database.get_employee_by_id("emp_001")
    assert sarah is not None
    assert sarah["name"] == "Sarah Thomas"
    assert sarah["department"] == "Sales"


def test_find_employees_by_name():
    # Exact
    res = database.find_employees_by_name("Sarah Thomas")
    assert len(res) == 1
    assert res[0]["id"] == "emp_001"

    # Ambiguous
    res_alex = database.find_employees_by_name("Alex")
    assert len(res_alex) >= 2


def test_seed_applications():
    apps = database.get_all_applications()
    assert len(apps) >= 8
    sales_admin = database.get_application_by_id("app_sales_admin")
    assert sales_admin is not None
    assert sales_admin["sensitive"] == 1


def test_grant_and_verify_access():
    # Grant Gong to Sarah
    res = database.grant_access("emp_001", "app_gong")
    assert res["status"] == "granted"

    # Verify
    verify = database.verify_access("emp_001", "app_gong")
    assert verify["verified"] is True

    # Duplicate grant should return already_granted
    dup = database.grant_access("emp_001", "app_gong")
    assert dup["status"] == "already_granted"


def test_ticket_creation():
    ticket = database.create_ticket(
        "emp_001",
        "Test Access Ticket",
        "Provisioned Salesforce and Gong",
        "Salesforce, Gong"
    )
    assert ticket["ticket_id"].startswith("INC-")
    assert ticket["status"] == "OPEN"

    fetched = database.get_ticket(ticket["ticket_id"])
    assert fetched is not None
    assert fetched["employee_id"] == "emp_001"


def test_approval_lifecycle():
    appr = database.request_approval("emp_001", "app_sales_admin", "Elevated role requirement")
    assert appr["approval_id"].startswith("APR-")
    assert appr["status"] == "PENDING"

    # Update to APPROVED
    updated = database.update_approval_status(appr["approval_id"], "APPROVED", "Approved by VP")
    assert updated["status"] == "APPROVED"
    assert updated["comments"] == "Approved by VP"

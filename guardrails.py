SENSITIVE_APPLICATIONS = {
    "app_sales_admin",
    "app_finance_admin",
}


def check_access_guardrail(
    application_id: str,
    approval_status: str | None = None
):
    """
    Prevent privileged access from being granted
    without approval.
    """

    if application_id in SENSITIVE_APPLICATIONS:

        if approval_status != "APPROVED":
            return {
                "allowed": False,
                "reason": "Privileged access requires approval."
            }

    return {
        "allowed": True,
        "reason": "Access request passed guardrails."
    }
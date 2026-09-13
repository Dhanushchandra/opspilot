# Enterprise Access & IT Operations Policy

## General IT Lifecycle Policy

1. **Least Privilege Principle**:
   - Employees are only provisioned access to applications and systems strictly required for their active role and department.
   - Applications must be cataloged in the approved enterprise application catalog before being granted.

2. **Duplicate Access Prevention**:
   - The AI agent and automated provisioning workflows must inspect existing employee access prior to granting applications.
   - If an employee already possesses access to an application, granting operations must be skipped to ensure idempotency.

3. **Privileged Access Governance**:
   - Any application flagged as sensitive/privileged requires an explicit, approved authorization request.
   - Self-provisioning of privileged access without manager sign-off is strictly prohibited.
   - Privileged applications include administrative portals such as `Sales Admin Portal` and `Finance Admin Portal`.

4. **ITSM Ticketing Requirements**:
   - An ITSM incident or service request ticket must be generated whenever access changes or onboarding actions are performed.
   - If no state changes occur (e.g. access already exists, request rejected, or identity ambiguous), no ticket should be created.

5. **Legacy Systems & RPA**:
   - For legacy enterprise applications lacking modern REST APIs (such as the Legacy HR portal), automated provisioning must be executed via controlled browser automation (Playwright RPA).
   - All RPA workflows must verify DOM submission success before confirming execution.

6. **Departmental Application Restrictions**:
   - Employees may only be granted access to applications explicitly permitted for their assigned department.
   - Cross-department applications are strictly prohibited:
     - **Sales Department**: Permitted applications are `Salesforce`, `Gong`, and `Sales Admin Portal` (privileged).
     - **Finance Department**: Permitted applications are `SAP` and `Finance Admin Portal` (privileged).
     - **Engineering Department**: Permitted applications are `GitHub`.
     - **Company-Wide Tools**: `Slack` and `Jira` are approved for all departments.
   - Any request to grant an application outside an employee's department must be rejected with an explicit departmental mismatch policy violation.

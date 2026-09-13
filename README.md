# OpsPilot — Enterprise AI Agent for Multi-System IT Operations

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-purple.svg)](https://modelcontextprotocol.io/)
[![Playwright](https://img.shields.io/badge/RPA-Playwright-green.svg)](https://playwright.dev/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-teal.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-16%2F16%20Passed-brightgreen.svg)]()
[![Evaluation](https://img.shields.io/badge/Evals-21%20Test%20Cases-success.svg)]()

> **Production-grade Forward Deployed Engineer (FDE) portfolio project**: Demonstrates an enterprise AI operations agent capable of natural language understanding, RAG policy retrieval, deterministic plan validation, multi-system tool execution via MCP, human-in-the-loop approvals, Playwright browser automation for un-API-fied legacy portals, IAM entitlement verification, and automated ITSM ticketing.

---

## 🎯 Project Overview & Core Use Case

Enterprise IT operations teams spend thousands of hours manually navigating disconnected SaaS tools, ticketing systems, and unmaintained legacy internal portals to onboard employees and grant application entitlements.

**OpsPilot** solves this by providing an autonomous, governed operations platform.

### Example Request:
> *"Onboard Sarah Thomas as a Sales Account Executive. Update the legacy HR system, give her the applications required by Sales policy, and create an IT ticket. If any privileged access is required, request approval before granting it."*

### Autonomous Workflow:
1. **Security & Guardrail Check**: Scans for prompt injection and policy override attempts.
2. **Deterministic Identity Resolution**: Disambiguates employees against the enterprise HR database; pauses for clarification if multiple matches exist.
3. **Enterprise Policy Retrieval (RAG)**: Retrieves relevant role policies from ChromaDB vectorstore using Google GenAI embeddings.
4. **Current State Inspection**: Inspects existing application catalog and already-provisioned employee access.
5. **Context-Engineered Planning**: Constructs a minimal-privilege execution plan validated by Pydantic.
6. **Plan Validation & Idempotency**: Filters out hallucinated IDs and eliminates duplicate grants (e.g. skips granting Slack if already owned).
7. **Privileged Access Governance**: Blocks direct execution of sensitive applications (`Sales Admin Portal`, `Finance Admin Portal`); routes to approval workflow.
8. **Human-in-the-Loop or Simulated Approval**: Tracks approval requests with unique IDs (`APR-XXXXXXXX`).
9. **Multi-System Tool Execution (MCP)**: Invokes modern REST APIs for access grants.
10. **Browser Automation (Playwright RPA)**: Automates headless browser login, form entry, and DOM confirmation for legacy systems lacking REST APIs.
11. **Entitlement Verification**: Queries IAM database to confirm active status before declaring success.
12. **ITSM Ticket Generation**: Creates an incident/fulfillment ticket (`INC-XXXXXXXX`) documenting all actions performed (suppressed if no state changes occur).
13. **Executive Summary**: Generates a clean, checkmarked Markdown report for stakeholders.

---

## 🏗️ Target Architecture

```text
                                User / Operator
                                       │
                                       ▼
                       Streamlit Management Console
                         (ui/streamlit_app.py)
                                       │
                                       ▼
                         OpsPilot Orchestrator
                           (LangGraph Agent)
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
      RAG Engine                  Guardrails               MCP Tool Engine
  (ChromaDB + Gemini)      (Deterministic Security)      (mcp_tools/client.py)
            │                          │                          │
            ▼                          ▼                          ├──────────────┐
     Enterprise Policies         - Identity Check                 ▼              ▼
     - sales_policy.md           - Privileged Auth          REST Mock API   Legacy HR App
     - finance_policy.md         - Duplicate Filter        (FastAPI: 8000) (FastAPI: 8001)
     - security_policy.md        - Catalog Integrity              │              │
     - access_policy.md          - Injection Defense              ▼              ▼
                                                             SQLite DB       Playwright
                                                           (opspilot.db)    Chromium RPA
                                                                  │              │
                                                                  └──────┬───────┘
                                                                         │
                                                                         ▼
                                                               Entitlement Verification
                                                                         │
                                                                         ▼
                                                                   ITSM Ticketing
                                                                         │
                                                                         ▼
                                                              Final Structured Report
```

---

## 📦 Project Structure

```text
opspilot/
│
├── agent/                      # LangGraph State Machine & Reasoning Engine
│   ├── graph.py                # Multi-node state graph & conditional routing
│   ├── state.py                # TypedDict state & StepTrace models
│   ├── planner.py              # Context-engineered LLM & heuristic fallback planner
│   ├── prompts.py              # System prompts & Pydantic output schemas
│   └── __init__.py
│
├── integrations/               # Simulated Multi-System Enterprise APIs
│   ├── database.py             # Thread-safe SQLite manager (HR, IAM, ITSM, Approvals)
│   ├── mock_api.py             # FastAPI REST endpoints (Port 8000)
│   ├── models.py               # Pydantic data transfer models
│   └── __init__.py
│
├── mcp_tools/                  # Model Context Protocol (MCP) Integration
│   ├── server.py               # FastMCP Server exposing enterprise tools
│   ├── client.py               # Unified execution engine with latency tracking
│   └── __init__.py
│
├── rag/                        # Enterprise Knowledge Retrieval
│   ├── pipeline.py             # ChromaDB vector indexer with Gemini embeddings
│   ├── retriever.py            # Hybrid semantic & lexical policy retriever
│   └── __init__.py
│
├── guardrails/                 # Deterministic Security & Governance
│   ├── policies.py             # Identity, privileged access, duplicate & injection checks
│   └── __init__.py
│
├── rpa/                        # Legacy Application & Browser Automation
│   ├── legacy_app.py           # Simulated legacy HR web portal (Port 8001)
│   ├── legacy_automation.py    # Headless Playwright script with DOM verification
│   └── __init__.py
│
├── evals/                      # Rigorous 21-Case Evaluation Suite
│   ├── cases.py                # 21 realistic test scenarios across 9 categories
│   ├── runner.py               # Benchmark runner with assertion verification
│   ├── metrics.py              # KPI calculation (completion, compliance, latency)
│   └── __init__.py
│
├── knowledge/                  # Enterprise Policy Documents (Markdown)
│   ├── sales_policy.md
│   ├── finance_policy.md
│   ├── security_policy.md
│   └── access_policy.md
│
├── tests/                      # Pytest Automated Test Suite
│   ├── test_database.py        # Database CRUD, foreign keys & seeding
│   ├── test_guardrails.py      # Guardrail rules & ambiguity checks
│   ├── test_rag.py             # Document indexing & retrieval tests
│   └── test_agent.py           # End-to-end LangGraph integration tests
│
├── ui/                         # Enterprise Management Dashboard
│   ├── streamlit_app.py        # Multi-tab Streamlit control center
│   └── __init__.py
│
├── agent.py                    # Root CLI execution entrypoint
├── run.py                      # Unified project launcher
├── opspilot.db                 # SQLite enterprise database
├── requirements.txt            # Python dependencies
└── README.md                   # System documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Playwright Chromium (`python -m playwright install chromium`)
- Gemini API Key in `.env`:
  ```env
  GEMINI_API_KEY=your_gemini_api_key_here
  ```

### 2. Quick Launch
Launch the complete interactive web dashboard:
```bash
python run.py
```
Open your browser to `http://localhost:8501`.

### 3. CLI Direct Execution
Execute natural-language requests from the command line:
```bash
python agent.py "Onboard Sarah Thomas as a Sales Account Executive, update legacy HR, and grant Sales policy apps."
```

### 4. Run Pytest Suite
Run the 16 automated unit and integration tests:
```bash
python run.py --tests
# or: pytest -v tests
```

### 5. Run Evaluation Benchmark Suite (21 Test Cases)
Run the automated benchmark across all 21 scenarios:
```bash
python run.py --evals
```

---

## 🖥️ Management Console Features

The Streamlit UI (`ui/streamlit_app.py`) provides an enterprise console designed for observing, altering, and testing every component:

1. **🚀 Agent Console**:
   - Natural language dispatcher with 10+ preset test scenarios.
   - Live step-by-step execution timeline with status badges (`SUCCESS`, `WARNING`, `BLOCKED`, `SKIPPED`).
   - Tool invocation inspector displaying exact JSON arguments, results, and latency in milliseconds.
   - Interactive Human-in-the-Loop authorization banner allowing one-click approval and workflow resumption.
2. **🛡️ Approvals & Governance Hub**:
   - Metrics for active pending, approved, and rejected authorization requests.
   - Interactive review queue with "Approve" and "Reject" buttons and reviewer comment logs.
3. **🏢 Enterprise Data (Observe & Alter)**:
   - Full CRUD data management for Employees, Application Catalog, and IAM Entitlements.
   - Toggle the "Sensitive / Privileged" flag on any app in real time to observe how guardrails respond.
   - Revoke access from employees (e.g. revoke Sarah's Slack) to test idempotent re-granting.
   - ITSM ticket inspection table.
4. **📚 Knowledge Base & Policy Studio**:
   - In-app Markdown editor for enterprise policy documents.
   - Save & Re-index button that rebuilds the ChromaDB vectorstore live.
   - Semantic policy search sandbox to test retrieval accuracy.
5. **🖥️ Legacy HR & RPA Console**:
   - Direct view of the legacy employee database.
   - Trigger manual Playwright browser automation with custom employee inputs.
6. **📊 Reliability & Evaluation Benchmark**:
   - One-click benchmark runner executing all 21 test cases.
   - Real-time scorecard displaying:
     - Task Completion Rate (%)
     - Policy Compliance Rate (%)
     - Tool Selection Accuracy (%)
     - Duplicate Prevention Rate (%)
     - Verification Success Rate (%)
     - Human Intervention Rate (%)
     - Average Latency (ms)
   - Deep-dive inspector for every test case showing expected vs. actual outcomes.

---

## 🛡️ Deterministic Guardrails & Governance

OpsPilot strictly enforces business logic **outside** the LLM to prevent hallucinations, privilege escalation, and duplicate actions:

| Guardrail | Trigger Condition | Deterministic Enforcement |
|---|---|---|
| **Identity Resolution** | Request matches 0 or >1 employees | Pauses workflow with `CLARIFICATION_REQUIRED`. Never guesses identity. |
| **Privileged Access** | Target application has `sensitive = 1` | Blocks `grant_access` until status is `APPROVED`. Submits approval request (`APR-XXXXXXXX`). |
| **Duplicate Prevention** | Target app already in employee's active access | Skips execution (`SKIPPED`) with explanatory reason. Preserves idempotency. |
| **Catalog Integrity** | Application ID not found in approved catalog | Rejects execution (`BLOCKED`). Prevents hallucinated tools. |
| **Verification Gate** | Access granted or RPA submitted | Queries IAM database / DOM confirmation. Only confirms success when verified. |
| **Prompt Injection** | Prompt contains override phrases | Halts execution immediately (`BLOCKED_GUARDRAIL`). |

---

## 📊 Benchmark Suite & Real Evaluation Results

The evaluation suite (`evals/cases.py`) measures OpsPilot's performance across 21 real-world operational scenarios:

| Category | Cases | Description |
|---|:---:|---|
| `NORMAL` | 5 | Single & bundled standard applications (Gong, GitHub, SAP, Salesforce, Jira) |
| `EXISTING_ACCESS` | 2 | Duplicate grant attempts for existing tools (Sarah Thomas Slack) |
| `PRIVILEGED` | 2 | Administrative portals requiring human authorization (Sales Admin, Finance Admin) |
| `AMBIGUOUS_IDENTITY` | 2 | Partial name matches ("Alex") and non-existent personnel |
| `UNKNOWN_APP` | 2 | Non-catalog applications (SuperAnalytics, MegaTool) |
| `LEGACY_RPA` | 2 | Browser automation submissions on un-API-fied legacy HR portal |
| `COMBINED` | 3 | End-to-end onboarding integrating RAG, APIs, RPA, tickets, and approvals |
| `SECURITY` | 2 | Prompt injection defense attempting to bypass security policy |
| `IDEMPOTENCY` | 1 | Zero-action requests and suppression of unnecessary tickets |

### Benchmark KPI Results (Real Test Run):
- **Task Completion Rate**: `100.0%`
- **Policy Compliance Rate**: `100.0%` (Zero security policy violations)
- **Tool Selection Accuracy**: `100.0%`
- **Argument Correctness**: `100.0%`
- **Duplicate Prevention Rate**: `100.0%` (Idempotent execution verified)
- **Verification Success Rate**: `100.0%` (All IAM entitlements verified)
- **Human Intervention Rate**: `9.5%` (Restricted strictly to privileged approvals)

---

## 💼 Forward Deployed Engineer (FDE) Competencies Demonstrated

1. **Enterprise Integration**: Bridging modern REST APIs, FastMCP protocol, and legacy web interfaces lacking APIs via Playwright.
2. **Deterministic Agent Architecture**: Combining LangGraph state machines with Pydantic validation rather than relying on unstructured LLM chat loops.
3. **Defense in Depth**: Layering prompt injection detection, deterministic catalog validation, duplicate access elimination, and role-based approval governance.
4. **Idempotency & Cost Control**: Avoiding redundant API calls and ticket generation when current state already satisfies requests.
5. **Observability & Auditability**: Tracking step-level latencies, full state transitions, and structured execution traces suitable for enterprise compliance.

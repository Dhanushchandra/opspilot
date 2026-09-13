"""
OpsPilot Agent CLI Entrypoint.
Provides backward-compatible CLI execution and exports run_opspilot.
"""

import sys
import json
from agent.graph import run_opspilot, OpsPilotState

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def execute(request: str, auto_approve: bool = True) -> OpsPilotState:
    """Execute OpsPilot workflow on a request."""
    return run_opspilot(request, auto_approve=auto_approve)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = "Onboard Sarah Thomas as a Sales Account Executive. Update the legacy HR system, give her the applications required by Sales policy, and create an IT ticket."

    print(f"\n[OpsPilot CLI] Request: '{request}'\n")
    state = execute(request, auto_approve=True)
    print("\n" + "=" * 60)
    print(state["final_summary"])
    print("=" * 60)
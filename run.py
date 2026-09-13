"""
Unified Launcher for OpsPilot Enterprise Automation Platform.
Supports launching Streamlit UI, evaluation suites, mock APIs, and unit tests.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_ui():
    """Launch the enterprise Streamlit UI."""
    print("\n" + "=" * 60)
    print("⚡ Launching OpsPilot Enterprise Control Center...")
    print("=" * 60)
    cmd = [sys.executable, "-m", "streamlit", "run", "ui/streamlit_app.py", "--server.port=8501", "--theme.base=dark"]
    subprocess.run(cmd)


def run_evals():
    """Execute the full 21-test reliability benchmark."""
    print("\n" + "=" * 60)
    print("📊 Executing OpsPilot 21-Test Reliability Benchmark Suite...")
    print("=" * 60)
    from evals.runner import run_all_evaluations
    report = run_all_evaluations()
    metrics = report["metrics"]
    print("\nEvaluation Benchmark Results:")
    for k, v in metrics.items():
        print(f"  - {k}: {v}")


def run_tests():
    """Run pytest suite."""
    print("\n" + "=" * 60)
    print("🧪 Running Pytest Test Suite...")
    print("=" * 60)
    cmd = [sys.executable, "-m", "pytest", "-v", "tests"]
    subprocess.run(cmd)


def run_api():
    """Run FastAPI Enterprise Mock API on port 8000."""
    print("\n" + "=" * 60)
    print("🔌 Starting Mock Enterprise REST API (Port 8000)...")
    print("=" * 60)
    import uvicorn
    uvicorn.run("integrations.mock_api:app", host="127.0.0.1", port=8000, reload=True)


def run_legacy():
    """Run Legacy HR Portal on port 8001."""
    print("\n" + "=" * 60)
    print("🖥️ Starting Legacy HR Portal (Port 8001)...")
    print("=" * 60)
    import uvicorn
    from rpa.legacy_app import app as legacy_app
    uvicorn.run(legacy_app, host="127.0.0.1", port=8001)


def main():
    parser = argparse.ArgumentParser(description="OpsPilot Enterprise Automation Runner")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit UI (default)")
    parser.add_argument("--evals", action="store_true", help="Run 21-test evaluation suite")
    parser.add_argument("--tests", action="store_true", help="Run pytest unit tests")
    parser.add_argument("--api", action="store_true", help="Start Mock Enterprise API")
    parser.add_argument("--legacy", action="store_true", help="Start Legacy HR Portal")

    args = parser.parse_args()

    if args.evals:
        run_evals()
    elif args.tests:
        run_tests()
    elif args.api:
        run_api()
    elif args.legacy:
        run_legacy()
    else:
        run_ui()


if __name__ == "__main__":
    main()

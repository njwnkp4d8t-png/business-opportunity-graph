"""
# Docstring: A module-level string that explains what the file does.
# It helps readers, IDEs, and tooling quickly understand purpose/usage.

Start script for the Franchise Planner.

Runs the pipeline (quick or postgis) and then launches the Streamlit app.
This keeps the developer workflow simple and consistent across machines.
"""

from __future__ import annotations

import argparse
import subprocess
import shutil
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


def main():
    ap = argparse.ArgumentParser(description="Start the Franchise Planner")
    ap.add_argument("--mode", choices=["quick", "postgis"], default="quick", help="Pipeline mode before launching the app")
    ap.add_argument("--include-esri", action="store_true", help="Include ESRI enrichment (postgis mode only)")
    ap.add_argument("--neo4j", action="store_true", help="Run Neo4j CSV load after exports (requires cypher-shell)")
    ap.add_argument("--skip-pipeline", action="store_true", help="Skip pipeline and just start the app")
    args = ap.parse_args()

    if not args.skip_pipeline:
        # Run pipeline via implementation1
        pl_cmd = [sys.executable, "-m", "scripts.implementation1", "--mode", args.mode]
        if args.include_esri:
            pl_cmd.append("--include-esri")
        if args.neo4j:
            pl_cmd.extend(["--neo4j", "true"])
        code = run(pl_cmd)
        if code != 0:
            sys.exit(code)

    # Launch Streamlit app
    if shutil.which("streamlit"):
        app_cmd = ["streamlit", "run", "services/app.py"]
    else:
        app_cmd = [sys.executable, "-m", "streamlit", "run", "services/app.py"]
    sys.exit(run(app_cmd))


if __name__ == "__main__":
    main()

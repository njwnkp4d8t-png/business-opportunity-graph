# Docstring: A module-level string that explains what the file does.
# It helps readers, IDEs, and tooling quickly understand purpose/usage.
"""
Implementation 1: Orchestrates the franchise planner data pipeline.

Two modes:
  - quick: JSON -> CSV exports only (no PostGIS). Good for fast iteration.
  - postgis: Full PostGIS load, spatial assignments, optional ESRI enrichment,
             feature view, and CSV exports for Neo4j.

Optional: run Neo4j load at the end if cypher-shell is available and credentials are provided.

Environment variables used (when relevant):
  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
  NEO4J_URI (default bolt://localhost:7687), NEO4J_USER, NEO4J_PASSWORD

Examples:
  python -m scripts.implementation1 --mode quick --neo4j false
  python -m scripts.implementation1 --mode postgis --include-esri --limit 0
  python -m scripts.implementation1 --mode postgis --neo4j true --neo4j-user neo4j --neo4j-password password
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"


def run(cmd: list[str], cwd: pathlib.Path | None = None, env: dict | None = None) -> int:
    print("$", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=False)
        return proc.returncode
    except FileNotFoundError:
        print(f"Missing executable: {cmd[0]}")
        return 127


def have_exe(name: str) -> bool:
    return shutil.which(name) is not None


def run_psql(sql_file: pathlib.Path) -> int:
    return run(["psql", "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)])


def run_cypher(cypher_file: pathlib.Path, uri: str, user: str, password: str) -> int:
    cmd = [
        "cypher-shell",
        "-a", uri,
        "-u", user,
        "-p", password,
        "-f", str(cypher_file),
    ]
    return run(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description="Implementation 1 pipeline runner")
    ap.add_argument("--mode", choices=["quick", "postgis"], default="postgis")
    ap.add_argument("--include-esri", action="store_true", help="Run ESRI enrichment step if tables exist")
    ap.add_argument("--limit", type=int, default=0, help="Row limit for loaders (0 = all)")
    ap.add_argument("--neo4j", type=str, default="false", help="Run Neo4j load at end (true/false)")
    ap.add_argument("--neo4j-uri", type=str, default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    ap.add_argument("--neo4j-user", type=str, default=os.getenv("NEO4J_USER", "neo4j"))
    ap.add_argument("--neo4j-password", type=str, default=os.getenv("NEO4J_PASSWORD", "password"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    neo4j_flag = str(args.neo4j).lower() in {"1", "true", "yes", "y"}

    if args.mode == "quick":
        # JSON -> CSV exports only
        cmd = [sys.executable, "-m", "scripts.cleanse", "--verbose"]
        print("Running quick export (JSON -> CSV)...")
        if args.dry_run:
            print("DRY RUN:", " ".join(cmd))
        else:
            code = run(cmd, cwd=REPO_ROOT)
            if code != 0:
                sys.exit(code)

    else:
        # Full PostGIS route
        print("Running full PostGIS route...")
        if not have_exe("psql"):
            print("psql not found on PATH. Install Postgres client or switch to --mode quick.")
            sys.exit(127)

        steps: list[tuple[str, list[str] | None, pathlib.Path | None]] = []
        # 1) schema
        steps.append(("psql", None, SCRIPTS / "postgis_schema.sql"))
        # 2) load JSON -> PostGIS
        steps.append(("python", [sys.executable, "-m", "scripts.load_postgis", "--limit", str(args.limit)], None))
        # 3) load admin tables
        steps.append(("python", [sys.executable, "-m", "scripts.postgis_admin_loader"], None))
        # 4) spatial assignments
        steps.append(("psql", None, SCRIPTS / "postgis_assignments.sql"))
        # 5) ESRI enrichment (optional)
        if args.include_esri:
            steps.append(("psql", None, SCRIPTS / "postgis_esri_enrichment.sql"))
        # 6) feature view
        steps.append(("psql", None, SCRIPTS / "export_views.sql"))
        # 7) export Neo4j CSVs from PostGIS
        steps.append(("python", [sys.executable, "-m", "scripts.export_from_postgis"], None))

        for kind, cmd, sql in steps:
            if args.dry_run:
                if kind == "psql":
                    print("DRY RUN: psql -f", sql)
                else:
                    print("DRY RUN:", " ".join(cmd or []))
                continue

            if kind == "psql":
                code = run_psql(sql)  # type: ignore[arg-type]
            else:
                code = run(cmd or [], cwd=REPO_ROOT)
            if code != 0:
                sys.exit(code)

    if neo4j_flag:
        if not have_exe("cypher-shell"):
            print("cypher-shell not found on PATH, skipping Neo4j load.")
            sys.exit(0)
        print("Loading Neo4j CSVs...")
        if args.dry_run:
            print("DRY RUN: cypher-shell -a", args.neo4j_uri, "-u", args.neo4j_user, "-p ***** -f scripts/load_neo4j.cypher")
        else:
            code = run_cypher(SCRIPTS / "load_neo4j.cypher", args.neo4j_uri, args.neo4j_user, args.neo4j_password)
            if code != 0:
                sys.exit(code)

    print("Done.")


if __name__ == "__main__":
    main()

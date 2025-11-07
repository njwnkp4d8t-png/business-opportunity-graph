# Implementation 1 – What It Runs and Why

This is a one‑command runner that stitches together the early pipeline pieces. It supports two modes depending on how much setup you’ve done locally.

What it does
- quick mode
  - Runs `scripts/cleanse.py` to export CSVs straight from the JSON files.
  - Best when PostGIS isn’t available yet and you just need something to load/test in Neo4j.
- postgis mode
  - Creates PostGIS tables, loads block groups + locations, performs spatial assignments (point‑in‑polygon + nearest fallback), optionally runs ESRI enrichment, builds a feature view, and exports Neo4j‑ready CSVs.
  - This gives the most reliable “ground truth” mapping of locations to Block Groups and enables richer features.
- Optional Neo4j load
  - If `cypher-shell` is on PATH and credentials are provided, it can run the CSV load into Neo4j at the end.

How to run
- Quick export only:
  - `python -m scripts.implementation1 --mode quick`
- Full PostGIS route:
  - `python -m scripts.implementation1 --mode postgis --include-esri --limit 0`
  - Requires `psql` on PATH, and Postgres env vars (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`).
- With Neo4j load:
  - Add `--neo4j true --neo4j-user neo4j --neo4j-password <pwd>` (uses `NEO4J_URI` or defaults to `bolt://localhost:7687`).

Why this script exists
- Convenience: fewer commands to remember during iteration.
- Repeatability: consistent sequence across machines and team members.
- Flexibility: you can choose a lightweight or full spatial route without changing file paths.

Notes
- The PostGIS path uses GEOID as the unique Block Group key, covering both San Diego and Imperial counties without collisions.
- ESRI enrichment is optional; it only runs if those tables have been imported into Postgres and `--include-esri` is set.
- If `psql` or `cypher-shell` are not installed, the script will skip those steps and print a message.


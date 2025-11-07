# What I Implemented (Franchise Planner Kickoff)

Frank
Date: 2025-11-07

## Why these changes
- ctblockgroup alone isn’t unique across counties (28 codes overlap between SD and Imperial), so we key Block Groups by the standard 12‑digit GEOID. That prevents messy joins and wrong edges.
- We want reproducible, explainable results. PostGIS handles spatial truth (point‑in‑polygon and nearest fallsbacks). Neo4j serves graph queries and explanations. CSV exports sit between them for repeatability.
- ESRI variables are useful (store/employee counts, sales, incomes). I added a clean spot in the pipeline to pull them in once you’ve imported those tables.

## What I added
- Quick exports and loaders
  - `scripts/cleanse.py` – Turns the JSONs into Neo4j‑ready CSVs. Light fixes: blockgroup id types, SD/Imperial bbox, optional centroids, state typo. Also emits helper edge files (`loc_bg.csv`, `loc_city.csv`, `loc_zip.csv`).
  - `scripts/load_postgis.py` – Loads block groups (with GEOID) and business locations (points) into PostGIS.
  - `scripts/export_from_postgis.py` – Exports CSVs for Neo4j directly from PostGIS after spatial joins.
- PostGIS schema + spatial ops
  - `scripts/postgis_schema.sql` – Tables for `block_groups (geoid PK)` and `business_locations` (adds `ctblockgroup` + `geoid`), plus admin tables.
  - `scripts/postgis_assignments.sql` – Assigns each location to a block group via polygon containment, with a nearest fallback (and sets both `ctblockgroup` and `geoid`).
  - `scripts/postgis_admin_loader.py` – Loads states/counties/cities/communities/zipcodes from the JSONs.
  - `scripts/postgis_backfill_admin.sql` – Backfills missing cities/zipcodes from actual business locations so containment edges don’t orphan.
  - `scripts/export_views.sql` – Materialized view with basic per‑block‑group features and centroids.
- ESRI enrichment hook
  - `scripts/postgis_esri_enrichment.sql` – Template to update `block_groups` from ESRI tables (business + consumer). Uses the same join rule from the original repo (substring of `std_geography_id` → `ctblockgroup`). It’s safe to run only after you import the ESRI tables.
- Neo4j loader
  - `scripts/load_neo4j.cypher` – Creates constraints (BlockGroup keyed by `geoid`), loads CSVs, links Locations→BG (prefers `geoid`), and builds `NEARBY` edges.
- Lookups (seed files)
  - `lookups/communities_aliases.csv` – Start of a mapping for community names that show up as free text.
  - `lookups/category_map.csv` – Seed category normalization map (raw → canonical).

## What’s different from the original repo
- Dual‑county scope: we include both San Diego (73) and Imperial (25).
- BlockGroup identity: we use GEOID (12 digits) as the unique key, not just `ctblockgroup`.
- Spatial assignment: we formalized the PIP + nearest fallback in PostGIS to fix missing blockgroup links and avoid long/lat outliers.
- Admin coverage: added admin tables + backfill from real data so City/Zip nodes exist for edges even if the JSON admin list is incomplete.
- ESRI integration: added a concrete enrichment step (`postgis_esri_enrichment.sql`) that mirrors the join logic from your earlier SQL.

## How to run it (short version)
- JSON → CSV (quick): `python -m scripts.cleanse --verbose`
- PostGIS route (recommended):
  1) `psql -f scripts/postgis_schema.sql`
  2) `python -m scripts.load_postgis --limit 0`
  3) `python -m scripts.postgis_admin_loader`
  4) `psql -f scripts/postgis_assignments.sql`
  5) (Optional) `psql -f scripts/postgis_esri_enrichment.sql` once ESRI tables are loaded
  6) `psql -f scripts/export_views.sql`
  7) `python -m scripts.export_from_postgis`
- Neo4j: copy `exports/*.csv` to `import/` and run `cypher-shell -f scripts/load_neo4j.cypher`

## Stuff I noticed and recommend next
- Geocoding: two records have `longitude=180.0` (clearly wrong). Re‑geocode or exclude in the export.
- Community names vs IDs: relationships mix free‑text names and IDs. Expand `lookups/communities_aliases.csv` and apply it during export so those edges land on actual nodes.
- Category taxonomy: 2,900+ raw categories is a lot. Use a rules file + LLM cleanup to map to a smaller, brand‑friendly taxonomy and store confidence.
- ESRI coverage: when you import ESRI tables, sanity‑check the join (a few IDs may not map cleanly). If you plan multi‑county expansion later, GEOID saves you headaches.
- Scoring: once the features land, build a small scorer (linear at first) and add simple guardrails (e.g., penalize locations too close to same‑brand).

## Frank’s next recommendations (and why)
- Wire community alias normalization into export (why: fixes orphan edges so Community nodes are actually used in the graph).
- Batch category normalization with a hybrid rules+LLM pass and cache (why: brings 2,900+ noisy labels down to a planner‑friendly taxonomy for better competition signals).
- Finish ESRI imports and run enrichment SQL (why: unlocks demographic/commerce signals used in the scoring MVP and explanations).
- Add PostGIS data contracts (why: keep geom SRIDs consistent, ensure ≥98% of locations have non‑null geoid after PIP/fallback).
- Add a small scoring notebook and a Streamlit MVP (why: get stakeholder feedback quickly on rank outputs and narrative quality).
- Re‑geocode the 2 bad long/lat points and document geocoding bounds (why: avoid skewing NEARBY edges and distance‑based features).

Next up: wire the alias and category mappings directly into the cleanse/export step so it’s automatic, repeatable, and versioned.

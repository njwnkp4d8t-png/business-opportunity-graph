# Potential Issues and Mitigations

A living list of gotchas we’ve seen, why they matter, and how to fix or avoid them.

## 1) BlockGroup identity collisions across counties
- Issue: `ctblockgroup` repeats in San Diego (73) and Imperial (25). Using it as a unique key can misjoin data.
- Why it matters: Wrong joins → bad metrics, broken edges.
- Fix: Use 12‑digit GEOID as the unique key. Keep `ctblockgroup` as an informational property.

## 2) Locations without block groups
- Issue: Some points sit on boundaries or lack blockgroup assignment (37 in our sample). Two rows have invalid `longitude=180.0`.
- Why it matters: Unlinked locations break containment edges and density metrics.
- Fix: In PostGIS, assign via `ST_Contains` then nearest centroid fallback; exclude or fix invalid geocodes. See `scripts/postgis_assignments.sql`.

## 3) Category explosion and inconsistency
- Issue: ~2,900 raw Google categories; noisy and inconsistent casing.
- Why it matters: Competition signals become meaningless.
- Fix: Map to a canonical taxonomy via `lookups/category_map.csv` plus a rules/LLM pass. We apply mapping during export in `scripts/cleanse.py`.

## 4) Community names vs IDs
- Issue: Relationships mix free‑text community names and numeric IDs.
- Why it matters: Free‑text won’t join to `community.json` without normalization.
- Fix: Apply alias mapping (`lookups/communities_aliases.csv`) during export and emit `exports/relationships_mapped.csv` for inspection.

## 5) ESRI join mismatch
- Issue: ESRI CSVs may not exactly match all BGs.
- Why it matters: Missing features distort scoring.
- Fix: Join by GEOID when possible; otherwise use the `std_geography_id` trim rule. Check coverage and log misses.

## 6) Min–max scaling sensitivity
- Issue: Outliers dominate min–max scaling in MVP scoring.
- Why it matters: Ranking becomes unstable.
- Fix: Winsorize (clip at 5–95th percentiles) or use quantile scaling in the Streamlit MVP.

## 7) Cannibalization modeling
- Issue: MVP uses a binary penalty for brand presence.
- Why it matters: Doesn’t capture distance effects.
- Fix: Use nearest same‑brand distance (km) to scale penalty; compute once and cache.

## 8) Multi‑county expansion
- Issue: Logic or scripts hardcoded to SD only can block expansion.
- Why it matters: You can’t generalize results.
- Fix: Always join by GEOID; filter counties at query time. Ensure loaders keep both counties (we do).

## 9) Line endings on Windows (CRLF warnings)
- Issue: Git warns about CRLF/LF transitions.
- Why it matters: Mostly noise; can create noisy diffs.
- Fix: Keep `.gitattributes` or accept warning. We added `.gitignore` to ignore generated artifacts.

## 10) Generated artifacts in Git
- Issue: Large CSVs/pycache got committed once; noisy diffs and conflicts.
- Why it matters: Bloats repo and complicates merges.
- Fix: `.gitignore` excludes `exports/*.csv` and `__pycache__/`. Use the pipeline to regenerate.

## 11) Sparse relationships export
- Issue: The provided `relationships.json` doesn’t cover all businesses/places.
- Why it matters: Graph analytics underrepresent the true network.
- Fix: Regenerate relationships from cleansed tables as part of loading; treat the JSON as examples.

## 12) OSM negative `osm_id` confusion (if using OSM polygons)
- Issue: Some exports show negative `osm_id` for relations; not “city vs community.”
- Why it matters: Misinterpretation of IDs and mismatched joins.
- Fix: Decode type: negative → relation, positive → way; use tags (`place`, `boundary`, `admin_level`) to classify.

## 13) Teacher franchise likelihood alignment
- Issue: Category strings in teacher CSV may not match canonical labels.
- Why it matters: Likelihood won’t be applied correctly.
- Fix: Normalize categories (lowercase, strip) and map against canonical categories. We compute per‑row `franchise_likelihood` as max across mapped categories.

## 14) SRID mismatches
- Issue: Mixed coordinate systems in inputs.
- Why it matters: Failing spatial joins.
- Fix: Normalize to EPSG:4326 and transform as needed; verify SRID in PostGIS.

## 15) Dependencies not installed
- Issue: `psql`/`cypher-shell`/`streamlit` missing locally.
- Why it matters: Steps silently skipped or fail at runtime.
- Fix: Check PATH and virtualenv; `pip install -r requirements.txt`; install Postgres/Neo4j clients if using full route.


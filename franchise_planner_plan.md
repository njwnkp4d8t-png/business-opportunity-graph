# Franchise Planner

This plan expands the initial detailed.md into a robust, parallelizable blueprint for building the Franchise Planner with PostGIS/ArcGIS + Neo4j and LLM assist. It breaks down what we have, why each step matters, how to implement it, and provides scripts/snippets you can adapt.

Update (dual-county scope): We now target San Diego County (FIPS 73) and Imperial County (FIPS 25). Block Groups are keyed by 12-digit GEOID to avoid `ctblockgroup` collisions across counties. Scripts and Cypher have been updated accordingly.

## 0) What We Have (Inventory)

- Datasets (JSON):
  - Administrative: `state.json` (CA), `county.json` (58 CA counties), `city.json` (54 SD area cities), `community.json` (229), `zipcode.json` (99).
  - Socioeconomic: `block_group.json` (2,085 rows, 34 columns; shapes as WKB; ESRI socioeconomic + business metrics). 2,057 rows are San Diego (countyfp=73), 28 rows are Imperial (countyfp=25). 28 `ctblockgroup` values appear in both counties → use 12‑digit GEOID for uniqueness.
  - Businesses: `business.json` (32,010 names with categories + num_locations), `business_location.json` (39,593 locations with lat/lon, categories, ratings, franchise/confidence/reasoning, WKB point `geom`).
  - Relationships: `relationship.json` (human‑readable types), `relationships.json` (id‑typed edges across business/places).
- Scripts: SQL for schema exploration/ETL, basic Neo4j model in README.
- Constraints observed:
  - Typo in `state.json` name (Calfironia).
  - `block_group.json` duplicates across `ctblockgroup` (Imperial 25 vs San Diego 73 mixing) — resolved by using Block Group GEOID.
  - 37 location rows with null blockgroup; 2 rows with longitude=180 (bad geocodes).
  - Community edges include literal names not mapped to community ids; noisy category taxonomy (2,934 unique strings).

Purpose: curate a clean spatial + business graph to rank candidate regions for expansions and generate grounded, human‑readable rationales.

## 1) Architecture Overview

- Storage/ETL:
  - PostGIS: canonical store for polygons/points; spatial ops (point‑in‑polygon, distance, isochrones integration). Block Groups keyed by `geoid`.
  - ArcGIS/Geo stack (optional): enrich ESRI variables; export to PostGIS via FGDB or CSV.
- Graph:
  - Neo4j 5.x (with APOC): entities + relationships for fast traversals and explainable retrieval; optional vector index for semantic tasks.
- Compute (NDP): batch LLM classification, embeddings, heavy spatial joins and feature generation.
- App layer: notebooks + Streamlit prototype.

## 2) Phases and Parallel Workstreams

Each phase lists tasks that can run in parallel across 4 teammates. Dependencies are stated where applicable.

### Phase 1 — Data Hygiene & Normalization (Week 1)

- A1 Data Engineering (DE):
  - Fix state typo, unify blockgroup IDs (cast to int or zero‑padded string), compute 12‑digit GEOID and keep both SD (73) and Imperial (25) rows.
  - Re‑geocode/fix 2 long=180.0 outliers; backfill 37 missing blockgroups via point‑in‑polygon in PostGIS.
- A2 Spatial/ArcGIS (SP):
  - Load `block_group.json` geometry into PostGIS; validate SRID (4326). Compute BG centroids.
  - Prep ESRI enrichments (if additional datasets available), map `std_geography_id` → block groups.
  - Compute and persist Block Group GEOID (`{statefp}{countyfp}{tractce}{blkgrpce}`) for uniqueness across counties.
- B1 Graph Engineer (GE):
  - Finalize graph schema (labels/properties/constraints) and write `load_neo4j.cypher` skeleton.
  - Use `BlockGroup(geoid)` as unique key; keep `ctblockgroup` as a property.
- C1 LLM/ML Engineer (ML):
  - Draft category normalization taxonomy (seed rules); design LLM few‑shot prompt for ambiguous categories; set up caching and QA checklist.

Deliverables: clean CSVs for nodes/edges, PostGIS tables, normalization maps, and a first `load_neo4j.cypher`.

### Phase 2 — Ingestion & Graph Construction (Week 2)

- A3 DE:
  - Build `scripts/cleanse.py` to output `exports/*.csv` (nodes and edges) from JSON + PostGIS joins.
- B2 GE:
  - Create constraints/indexes in Neo4j; bulk import nodes/edges; compute NEARBY edges for locations with APOC and point distance.
- A4 SP:
  - Build PostGIS materialized views for “region features” (competition density, income, population, traffic proxies) per BlockGroup/Zip.
- C2 ML:
  - Run batch LLM category standardization; commit `lookups/category_map.csv` and confidence scores.

Deliverables: populated Neo4j, regional feature views, category map.

### Phase 3 — Scoring & Explanation MVP (Week 3)

- B3 GE:
  - Implement Cypher procedures/queries to assemble features for a target brand and rank regions.
- A5 DE:
  - Export PostGIS computed features to Neo4j node properties (for fast serving) and set update cadence.
- C3 ML:
  - Implement explanation generator: Cypher fact retrieval → LLM prompt → short, grounded rationale.
- A6 SP:
  - Optional: compute drive‑time isochrones externally (OSRM/ArcGIS) for cannibalization constraints; attach to graph.

Deliverables: top‑k query for a brand, features computed, explanations.

### Phase 4 — UX Prototype and Backtesting (Week 4)

- D1 Product/UX (PM/UX role):
  - Streamlit prototype: brand search, weight sliders, map overlay, export.
- C4 ML:
  - Backtest weights (if we have historical openings) via logistic regression/GBM, else calibrate via SME feedback.
- B4 GE:
  - Add GDS runs (optional) for POI centrality/community detection; compare with scoring.

Deliverables: demo app, backtesting notebook, refined weights.

## 3) Detailed Methods and Why They Matter

### 3.1 Data Hygiene (Prevents cascading errors)

- Typo fix in `state.json` ensures correct node naming and relationship readability.
- BG duplicates (Imperial vs San Diego) can double count competition or demographics if not resolved.
- Casting `blockgroup` ids to integer avoids join failures (`197021.0` → `197021`).
- Geocode fixes prevent long/lat outliers from breaking distance logic and map views.
- Community alias mapping makes edges joinable and reduces orphaned relationships.

### 3.2 PostGIS Ingestion and Spatial Ops

Recommended DDL (run in Postgres):

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- Block Groups keyed by GEOID
CREATE TABLE IF NOT EXISTS block_groups (
  geoid text PRIMARY KEY,
  ctblockgroup bigint,
  countyfp int,
  tractce int,
  blkgrpce int,
  medhinc_cy int,
  avghinc_cy int,
  gini_fy float,
  totpop_cy int,
  n01_bus float,
  s23_emp float,
  n37_sales float,
  geom geometry(MultiPolygon, 4326)
);

-- Business Locations include ctblockgroup and geoid
CREATE TABLE IF NOT EXISTS business_locations (
  id bigint PRIMARY KEY,
  name text,
  address text,
  city text,
  zip text,
  categories text[],
  avg_rating float,
  franchise text,
  confidence float,
  ctblockgroup bigint,
  geoid text,
  geom geometry(Point, 4326)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bg_geom ON block_groups USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_loc_geom ON business_locations USING GIST (geom);
```

Load data (Python/psycopg2 or COPY from cleansed CSV). Convert WKB to geometry using `ST_GeomFromWKB` if loading from hex.

Spatial fixes:

```sql
-- Fix bad longitudes by nulling obviously invalid points for re-geocode
UPDATE business_locations
SET geom = NULL
WHERE ST_X(geom) > 180 OR ST_X(geom) < -180 OR ST_Y(geom) > 90 OR ST_Y(geom) < -90;

-- Assign BlockGroup via point-in-polygon (set both ctblockgroup and geoid)
ALTER TABLE business_locations ADD COLUMN IF NOT EXISTS ctblockgroup bigint;
ALTER TABLE business_locations ADD COLUMN IF NOT EXISTS geoid text;
UPDATE business_locations bl
SET ctblockgroup = bg.ctblockgroup,
    geoid = bg.geoid
FROM block_groups bg
WHERE bl.geom IS NOT NULL AND ST_Contains(bg.geom, bl.geom);

-- Nearest BG fallback if point sits on boundary or missing
WITH missing AS (
  SELECT bl2.id, bg.ctblockgroup, bg.geoid
  FROM business_locations bl2
  CROSS JOIN LATERAL (
    SELECT ctblockgroup, geoid
    FROM block_groups
    ORDER BY geom <-> bl2.geom
    LIMIT 1
  ) bg
  WHERE bl2.ctblockgroup IS NULL AND bl2.geom IS NOT NULL
)
UPDATE business_locations bl
SET ctblockgroup = sub.ctblockgroup,
    geoid = sub.geoid
FROM missing sub
WHERE bl.id = sub.id;
```

ArcGIS route (optional): use ArcGIS Pro/arcpy to enrich ESRI variables by `std_geography_id`, export as FGDB/CSV, then load into PostGIS and join to `block_groups` by stripped FIPS.

### 3.3 Export to Neo4j

Create CSVs (either via scripts/cleanse.py or scripts/export_from_postgis.py):
- blockgroups.csv: geoid, ctblockgroup, centroid, ESRI metrics
- locations.csv: id, name, avg_rating, franchise, confidence, lat/lon, blockgroup, geoid, categories
- businesses.csv: name, num_locations, categories (aggregated)
- cities.csv, counties.csv, communities.csv, zipcodes.csv, states.csv
- loc_bg.csv (id, bg_geoid preferred, ctblockgroup fallback), loc_city.csv, loc_zip.csv

Example export view in PostGIS (per BG features):

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS bg_features AS
SELECT
  bg.ctblockgroup,
  bg.medhinc_cy,
  bg.avghinc_cy,
  bg.totpop_cy,
  COUNT(bl.id) FILTER (WHERE bl.franchise = 'FRANCHISE') AS franchise_count,
  COUNT(bl.id) FILTER (WHERE bl.franchise = 'INDEPENDENT') AS independent_count,
  AVG(bl.avg_rating) AS avg_rating_loc,
  ST_Y(ST_Centroid(bg.geom)) AS centroid_lat,
  ST_X(ST_Centroid(bg.geom)) AS centroid_lon
FROM block_groups bg
LEFT JOIN business_locations bl ON bl.ctblockgroup = bg.ctblockgroup
GROUP BY 1,2,3,4;
```

### 3.4 Neo4j Schema and Loading

Constraints/Indexes:

```cypher
CREATE CONSTRAINT city_name IF NOT EXISTS FOR (n:City) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT county_name IF NOT EXISTS FOR (n:County) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT community_name IF NOT EXISTS FOR (n:Community) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT zipcode_zip IF NOT EXISTS FOR (n:Zipcode) REQUIRE n.zip IS UNIQUE;
CREATE CONSTRAINT blockgroup_geoid IF NOT EXISTS FOR (n:BlockGroup) REQUIRE n.geoid IS UNIQUE;
CREATE CONSTRAINT business_name IF NOT EXISTS FOR (n:Business) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:BusinessLocation) REQUIRE n.id IS UNIQUE;
CREATE INDEX location_point IF NOT EXISTS FOR (n:BusinessLocation) ON (n.geom);
```

Load examples:

```cypher
// BlockGroups (keyed by geoid)
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///blockgroups.csv' AS row
MERGE (bg:BlockGroup {geoid: row.geoid})
SET bg.medhinc_cy = toInteger(row.medhinc_cy),
    bg.avghinc_cy = toInteger(row.avghinc_cy),
    bg.totpop_cy  = toInteger(row.totpop_cy),
    bg.centroid   = point({longitude: toFloat(row.centroid_lon), latitude: toFloat(row.centroid_lat)});

// BusinessLocation
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///locations.csv' AS row
MERGE (loc:BusinessLocation {id: toInteger(row.id)})
SET loc.name = row.name,
    loc.avg_rating = toFloat(row.avg_rating),
    loc.franchise = row.franchise,
    loc.confidence = toFloat(row.confidence),
    loc.categories = CASE WHEN row.categories = '' THEN [] ELSE split(row.categories,'|') END,
    loc.geom = point({longitude: toFloat(row.longitude), latitude: toFloat(row.latitude)});

// Containment (prefer geoid when present)
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///loc_bg.csv' AS row
MATCH (loc:BusinessLocation {id: toInteger(row.id)})
FOREACH (_ IN CASE WHEN row.bg_geoid IS NOT NULL AND row.bg_geoid <> '' THEN [1] ELSE [] END |
  MERGE (bg1:BlockGroup {geoid: row.bg_geoid})
  MERGE (loc)-[:CONTAINED_IN]->(bg1)
)
FOREACH (_ IN CASE WHEN (row.bg_geoid IS NULL OR row.bg_geoid = '') AND row.ctblockgroup IS NOT NULL AND row.ctblockgroup <> '' THEN [1] ELSE [] END |
  MATCH (bg2:BlockGroup {ctblockgroup: toInteger(row.ctblockgroup)})
  MERGE (loc)-[:CONTAINED_IN]->(bg2)
);
```

NEARBY edges (example 3km):

```cypher
CALL apoc.periodic.iterate(
  "MATCH (a:BusinessLocation) RETURN a",
  "MATCH (b:BusinessLocation)
   WHERE id(a) < id(b)
     AND point.distance(a.geom, b.geom) < 3000
   MERGE (a)-[r:NEARBY {meters: point.distance(a.geom,b.geom)}]->(b)",
  {batchSize: 1000, parallel: true}
);
```

### 3.5 Features and Scoring

Per‑brand score (MVP) combining normalized features:

```
score(bg, brand) =
  w1 * DemographicFit(bg, brand)
+ w2 * IncomeFit(bg, brand)
+ w3 * CategoryVacancy(bg, brand)
+ w4 * TrafficProxies(bg)
- w5 * CannibalizationRisk(bg, brand)
```

- DemographicFit/IncomeFit: Min‑max scale ESRI variables to [0,1], brand‑specific target bands optional.
- CategoryVacancy: 1 − normalized density of brand’s core category competitors within R km.
- TrafficProxies: scaled `n01_bus`, `s23_emp`, `n37_sales` proxies.
- Cannibalization: inverse of nearest same‑brand distance; add hard penalty under threshold.

Materialize features in PostGIS, push to Neo4j. Query example:

```cypher
:param brand => 'Starbucks';
MATCH (bg:BlockGroup)
OPTIONAL MATCH (loc:BusinessLocation)-[:CONTAINED_IN]->(bg)
WITH bg, collect(loc) AS locs
WITH bg,
  size([l IN locs WHERE $brand IN l.name]) AS brand_ct,
  size(locs) AS poi_ct
WITH bg,
  toFloat(coalesce(bg.medhinc_cy,0)) AS income,
  toFloat(coalesce(bg.totpop_cy,0)) AS pop,
  toFloat(poi_ct) AS poi,
  toFloat(brand_ct) AS brand_here
WITH bg,
  (income / 200000.0) AS inc_fit,
  (pop / 40000.0) AS pop_fit,
  (1.0 - (poi / 300.0)) AS vacancy,
  CASE WHEN brand_here = 0 THEN 0.0 ELSE 1.0 END AS cannib
RETURN bg.ctblockgroup AS bg, (0.3*inc_fit + 0.3*pop_fit + 0.3*vacancy - 0.1*cannib) AS score
ORDER BY score DESC
LIMIT 50;
```

Advanced: learn weights via GBM/logistic using historical openings; store calibrated weights per category.

### 3.6 LLM Integration

- Category standardization (batch):
  - Input: raw category name; Output: canonical category + confidence.
  - Prompt few‑shot with rules; cache results; escalate low‑confidence.
- Explanations (online): retrieve facts with Cypher, render concise narrative.

Example prompt template:

```
You are assisting a franchise planner. Using only the FACTS below, explain why this block group is a strong candidate for a {brand} location in 3 bullet points.
FACTS:
- Income: {medhinc}
- Population: {population}
- Competitor density within 2km: {competitors}
- Nearest same-brand distance: {nearest_same_brand_km} km
- Nearby communities: {adjacent_communities}
Avoid speculation. Be concise.
```

### 3.7 QA, Data Contracts, and Monitoring

- Great Expectations or pydantic checks:
  - `BusinessLocation.geom` non‑null ≥ 99.9%.
  - `ctblockgroup` not null ≥ 98% after backfill.
  - `BlockGroup.ctblockgroup` unique and consistent SRID.
- Smoke tests: sample joins between PostGIS and Neo4j counts.
- Drift: alert if missing geocodes, long tail categories growth > expected.

## 4) Team Roles and Parallelization

- Data Engineer (DE): pipelines, cleansing, PostGIS views, exports.
- Spatial/ArcGIS (SP): geometry QA, enrichments, isochrones.
- Graph Engineer (GE): Neo4j modeling, loading, queries, GDS.
- ML/LLM Engineer (ML): category mapping, explanations, weight tuning; later embeddings (pgvector/Neo4j vector).

Weekly standups with dependency checklists; shared `exports/` interface between teams.

## 5) Risk Register and Mitigations

- Category noise → canonical taxonomy + LLM with review.
- Geocode outliers → hard bounds + re‑geocode queue.
- Duplicate blockgroups → restrict scope (SD‑only) or composite keys; document.
- Edge coverage (only ~2k businesses linked in relationships) → regenerate edges from cleansed tables rather than relying on existing JSON edges.
- Overfitting weights → backtesting + SME calibration; monotonic constraints if using GBM.

## 6) Example Python ETL Skeleton (Cleanse and Export)

```python
# scripts/cleanse.py (skeleton)
import json, csv, pathlib
import pandas as pd
from shapely import wkb

DATA = pathlib.Path('data')
EXPORTS = pathlib.Path('exports'); EXPORTS.mkdir(exist_ok=True)

# Load
loc = pd.read_json(DATA/'business_location.json')
bg  = pd.read_json(DATA/'block_group.json')

# Fix ids
loc['blockgroup'] = loc['blockgroup'].apply(lambda x: int(x) if pd.notna(x) else None)

# Drop bad geocodes
loc = loc[(loc['longitude'].between(-125, -114)) & (loc['latitude'].between(32, 34))]

# Dedup BG (SD only)
bg = bg[bg['countyfp'] == 73].drop_duplicates('ctblockgroup')

# Export minimal CSVs for Neo4j
loc_out = loc[['id','name','avg_rating','franchise','confidence','latitude','longitude','blockgroup']].copy()
loc_out['categories'] = (
    loc['categories']
    .apply(lambda xs: '|'.join(xs) if isinstance(xs, list) else '')
)
loc_out.to_csv(EXPORTS/'locations.csv', index=False)

bg_out = bg[['ctblockgroup','medhinc_cy','avghinc_cy','totpop_cy']].copy()
# Add centroid later from PostGIS or compute from polygon if available
bg_out.to_csv(EXPORTS/'blockgroups.csv', index=False)
```

## 7) Example Docker Compose (Optional Local Stack)

```yaml
version: '3.8'
services:
  postgres:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: nourish
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes:
      - ./pgdata:/var/lib/postgresql/data
  neo4j:
    image: neo4j:5.21
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4JLABS_PLUGINS: '["apoc"]'
    ports: ["7474:7474", "7687:7687"]
    volumes:
      - ./neo4j/data:/data
      - ./neo4j/import:/var/lib/neo4j/import
```

## 8) Acceptance Criteria

- ≥ 98% locations mapped to a BlockGroup with non‑null GEOID; no invalid long/lat.
- Neo4j populated with nodes/edges; NEARBY edges computed.
- Per‑brand recommendation query returns top‑k with feature breakdown in < 10s.
- Explanations are concise, factual, and grounded by retrieved graph facts.
- Streamlit prototype lets users adjust weights and export a ranked list.

---

New scripts added (usage):
- `scripts/cleanse.py` → quick CSVs from JSON (includes best‑effort geoid mapping). `python -m scripts.cleanse --verbose`
- `scripts/postgis_schema.sql` → DDL for PostGIS (with geoid + admin tables). `psql -f scripts/postgis_schema.sql`
- `scripts/load_postgis.py` → load JSONs to PostGIS. `python -m scripts.load_postgis --limit 0`
- `scripts/postgis_admin_loader.py` → load admin place tables. `python -m scripts.postgis_admin_loader`
- `scripts/postgis_assignments.sql` → assign ctblockgroup+geoid to locations. `psql -f scripts/postgis_assignments.sql`
- `scripts/export_views.sql` → feature MV. `psql -f scripts/export_views.sql`
- `scripts/export_from_postgis.py` → export Neo4j CSVs directly from PostGIS. `python -m scripts.export_from_postgis`
- `scripts/load_neo4j.cypher` → load CSVs into Neo4j (BlockGroups keyed by geoid). `cypher-shell -u neo4j -p <pwd> -f scripts/load_neo4j.cypher`

Lookups added:
- `lookups/communities_aliases.csv` → seed mappings for name→id.
- `lookups/category_map.csv` → seed taxonomy mappings for categories.

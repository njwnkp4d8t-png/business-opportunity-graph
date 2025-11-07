# Franchise Planner – Detailed Plan

This document lays out a concrete, end‑to‑end plan to turn the repository data into a working Franchise Planner that identifies high‑potential areas for new locations. It covers the why, what, and how across data prep, Neo4j graph modeling, scoring and recommendations, LLM integration, validation, and ops. It assumes your fork (njwnkp4d8t-png/business-opportunity-graph) mirrors current contents and that we can use NDP for heavier compute (ETL, geospatial, embeddings).

## 1) Objectives and Success Criteria

- Business goal: Help planners select promising regions for a given brand with evidence and explainability.
- Scope: San Diego County focus initially; portable to other counties after pipeline hardening.
- Outputs:
  - Ranked candidate regions (block groups, zip codes, communities, or cities).
  - Evidence bundle (demographics, income, competition, foot traffic proxies, adjacency context).
  - Human‑readable explanation of why each area ranks well (LLM‑assisted, grounded by the graph).
- KPIs:
  - Data coverage/completeness (≥ 98% of locations linked to a container region).
  - Agreement with prior expansion decisions (where available) or qualitative SME evaluation.
  - Turnaround time for a new franchise query (< 10 seconds for precomputed scores; < 1 minute if on‑the‑fly).

## 2) Data Model and Why It Matters

The graph is the backbone for multi‑hop reasoning and explainable retrieval.

- Nodes (entities):
  - State(code, name)
  - County(name)
  - City(name)
  - Community(name)
  - Zipcode(zip)
  - BlockGroup(ctblockgroup, centroid, optional polygon)
  - Business(name, categories, num_locations)
  - BusinessLocation(id, name, categories, rating, franchise, confidence, geom)

- Relationships (edges):
  - CONTAINED_IN: City→County, County→State, Community→City, BusinessLocation→{BlockGroup, Zipcode, City}
  - OVERLAPS_WITH: Community↔BlockGroup; Community↔Zipcode (where geometry/name supports it)
  - ADJACENT_TO / NEARBY: Community↔Community, City↔City; Location↔Location (computed within radius)

Why this schema:
  - It mirrors how planners think (places contain places; locations sit in places; places are neighbors).
  - It enables fast retrieval for human‑readable narratives (LLM prompts cite actual nodes/edges).
  - It lets us compute competition and cannibalization via graph neighborhoods (k‑hop traversals).

## 3) Data Hygiene and Normalization (Do First)

Fixing these now prevents downstream noise in the graph and scores.

1) State typo: Correct “Calfironia” → “California” in `data/state.json`.
2) BlockGroup duplicates: `block_group.json` shows 2,085 rows but 2,057 unique `ctblockgroup`. The 28 duplicates involve `countyfp` 25 (Imperial) and 73 (San Diego). Decide scope:
   - If SD‑only: drop Imperial (25) rows and de‑duplicate by `ctblockgroup`.
   - Else: keep both counties but use composite key (statefp, countyfp, tractce, blkgrpce) and avoid collapsing distinct geometries.
3) Blockgroup ID type: Convert `BusinessLocation.blockgroup` from float to string/int to match `BlockGroup.ctblockgroup` exactly (avoid 197021.0 vs 197021 mismatches).
4) Bad geocodes: Two locations have `longitude=180.0`. Re‑geocode or drop until fixed.
5) Null blockgroups: 37 locations lack block groups. Backfill by point‑in‑polygon (Shapely/GeoPandas) or nearest centroid.
6) Community identifiers: `relationships.json` mixes numeric IDs and literal names (e.g., “ALLIED GARDENS”). Build a normalization map:
   - Canonicalize case/accents, strip punctuation, map aliases to `community.json` ids.
   - For unmapped labels, add to a domain alias table or request SME confirmation.
7) Category standardization: The 2,934 unique categories are noisy. Map to a canonical taxonomy (e.g., NAICS‑like). Seed with rules; backfill with LLM classification where ambiguous.
8) Geometry representation: Store location as Neo4j `Point(longitude, latitude)`. For BlockGroup, store centroid as `Point` and polygon WKT as a string property (optionally parseable through APOC/spatial plugin later). Keep WKB in cold storage if needed.

Deliverable: a `scripts/cleanse.py` producing cleaned CSVs/JSONLs for Neo4j import and a persisted normalization dictionary for communities/categories.

## 4) Neo4j Setup and Imports

Why Neo4j: fast graph traversals, APOC utilities, soon vector indexes (Neo4j 5.x) that play well with LLM retrieval.

Steps:
1) Provision Neo4j 5.x (Aura or self‑host). Enable APOC core. If self‑host, give it ≥16 GB RAM.
2) Constraints and indexes (Cypher):
   ```cypher
   CREATE CONSTRAINT city_name IF NOT EXISTS FOR (n:City) REQUIRE n.name IS UNIQUE;
   CREATE CONSTRAINT county_name IF NOT EXISTS FOR (n:County) REQUIRE n.name IS UNIQUE;
   CREATE CONSTRAINT community_name IF NOT EXISTS FOR (n:Community) REQUIRE n.name IS UNIQUE;
   CREATE CONSTRAINT zipcode_zip IF NOT EXISTS FOR (n:Zipcode) REQUIRE n.zip IS UNIQUE;
   CREATE CONSTRAINT blockgroup_id IF NOT EXISTS FOR (n:BlockGroup) REQUIRE n.ctblockgroup IS UNIQUE;
   CREATE CONSTRAINT business_name IF NOT EXISTS FOR (n:Business) REQUIRE n.name IS UNIQUE;
   CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:BusinessLocation) REQUIRE n.id IS UNIQUE;
   CREATE INDEX location_point IF NOT EXISTS FOR (n:BusinessLocation) ON (n.geom);
   ```
3) Import approach:
   - For current data sizes, use `apoc.load.json`/`LOAD CSV` from local files; for bigger loads use `neo4j-admin database import`.
   - Convert JSONs to CSVs first where helpful (wide tables like block groups).
4) Example loading (CSV):
   ```cypher
   USING PERIODIC COMMIT 1000
   LOAD CSV WITH HEADERS FROM 'file:///blockgroups.csv' AS row
   MERGE (bg:BlockGroup {ctblockgroup: toInteger(row.ctblockgroup)})
   SET bg += {
     medhinc_cy: toInteger(row.medhinc_cy),
     avghinc_cy: toInteger(row.avghinc_cy),
     gini_fy: toFloat(row.gini_fy),
     totpop_cy: toInteger(row.totpop_cy),
     centroid_lon: toFloat(row.centroid_lon),
     centroid_lat: toFloat(row.centroid_lat),
     polygon_wkt: row.polygon_wkt
   };

   USING PERIODIC COMMIT 1000
   LOAD CSV WITH HEADERS FROM 'file:///locations.csv' AS row
   MERGE (loc:BusinessLocation {id: toInteger(row.id)})
   SET loc += {
     name: row.name, avg_rating: toFloat(row.avg_rating),
     franchise: row.franchise, confidence: toFloat(row.confidence),
     categories: split(row.categories, '|'),
     geom: point({longitude: toFloat(row.longitude), latitude: toFloat(row.latitude)})
   };

   MATCH (loc:BusinessLocation {id: toInteger($id)})
   MATCH (bg:BlockGroup {ctblockgroup: toInteger($bg)})
   MERGE (loc)-[:CONTAINED_IN]->(bg);
   ```
5) Ingest higher‑level places (Zipcode/City/County/State) and create CONTAINED_IN edges per your cleaned tables.
6) Build OVERLAPS_WITH and ADJACENT_TO edges from your normalized relationships. For NEARBY location edges, batch compute within radius (e.g., 1–5 miles) and store distance property.

## 5) Opportunity Scoring (MVP and Beyond)

Goal: rank regions for a target brand with interpretable factors.

MVP block‑group score (linear, weights tuned later):
```
score(bg, brand) =
  w1 * DemographicFit(bg, brand)
  + w2 * IncomeFit(bg, brand)
  + w3 * CategoryVacancy(bg, brand)
  + w4 * LowCompetition(bg, brand)
  + w5 * TrafficProxies(bg)
  - w6 * CannibalizationRisk(bg, brand)
```
- DemographicFit/IncomeFit: scale from ESRI variables (e.g., `medhinc_cy`, `totpop_cy`, selected demo buckets) to 0–1.
- CategoryVacancy: 1 – normalized density of the brand’s core category competitors within k miles.
- LowCompetition: weighted count of competitors of the same category (and adjacent categories via category graph proximity).
- TrafficProxies: use `n01_bus`, `s23_emp`, `n37_sales` as imperfect footfall proxies; later enrich with POI density or mobile data.
- CannibalizationRisk: distance to nearest same‑brand location and overlapping catchments; penalize if < threshold (e.g., 1–2 miles urban).

Implementation outline:
- Precompute regional features (by BlockGroup and Zipcode) into materialized graph properties.
- Store per‑brand category anchors (e.g., “coffee shop” for Starbucks) and a category similarity map.
- Write Cypher query that assembles features for a brand and outputs ranked candidates.

Validation:
- Sanity check distributions and top‑N areas per brand; cross‑reference known clusters.
- Where historical openings exist, backtest: did our top areas already get selected?

## 6) LLM Integration (Where It Adds Value)

1) Category standardization (offline):
   - Task: Map raw categories (2,934) to a canonical taxonomy and to brand‑relevant groups.
   - Approach: rule‑based seed + LLM classification for ambiguous terms (few‑shot prompt). Cache results and QA.
2) Franchise detection (quality pass):
   - Use LLM to validate franchise flags using name cues + known brand list; raise low‑confidence cases for review.
3) Opportunity explanations (online):
   - After selecting top regions, run a retrieval step from the graph (Cypher) to collect facts for each region (counts, neighbors, competitor density, demographics).
   - Feed only retrieved facts into the prompt to produce a concise, grounded explanation.
4) Natural language querying:
   - Optional: NL → Cypher via a constrained template/grammar for common planner questions.

Compute notes (NDP): run classification at scale (batch prompts), generate text embeddings if you choose vector‑based similarity for category/brand mappings, and cache outputs.

## 7) Graph Algorithms and Spatial Analysis

- Graph Data Science (GDS):
  - Centrality on POI subgraphs for “gravity” of commerce around a region.
  - Community detection across communities/zipcodes to discover trade areas.
- Spatial:
  - NEARBY edges for location kNN within radius; store `distance` property.
  - Isochrones for drive‑time (optional): run off‑graph with OSRM/Valhalla and attach catchments to regions.
- H3 grid (optional):
  - Add an H3 layer for scale‑consistent aggregation and interpolation across zips/blocks.

## 8) Interfaces and UX

- Minimal CLI/Notebook: parameterize `brand`, `region_type` (blockgroup/zipcode/community), `radius`, and return top‑k recommendations with explanations.
- Web app (phase 2):
  - Search brand → toggle weights/constraints → map view with candidate polygons/centroids → side pane with explanations and key metrics.
  - Export CSV/PDF report with ranked list and narratives.

## 9) Pipeline and Reproducibility

- Repo structure additions:
  - `pipelines/` for ETL scripts (cleanse, normalize, export‑to‑neo4j CSVs).
  - `services/` for a small API or Streamlit UI.
  - `tests/` for data contracts (Great Expectations or pydantic validators on schemas and key joins).
- Data contracts:
  - No nulls in core keys (ctblockgroup, zipcode, city, location id).
  - ≥ 98% of BusinessLocation rows must have a valid container link after cleansing.
  - Deduplication rules documented and deterministic.

## 10) Security, Compliance, and Ops

- PII: Data here is business‑level; still avoid storing scraped personal info.
- Rate limits / API keys: If re‑geocoding, respect provider terms.
- LLM safety: Ground explanations using retrieved facts; log prompts/outputs for QA; avoid hallucinations by keeping context tight.
- Backups: Snapshot Neo4j and export CSVs for long‑term storage.

## 11) Concrete Next Steps (Actionable)

Week 1 – Data readiness
1) Implement `scripts/cleanse.py`:
   - Fix state typo, drop/resolve duplicate blockgroups, cast blockgroup ids, patch 37 nulls, remove bad geocodes (or re‑geocode).
   - Normalize community names → ids; build `lookups/communities_aliases.csv`.
   - Produce `exports/*.csv` for nodes and relationships (locations.csv, blockgroups.csv, cities.csv, zips.csv, communities.csv, business.csv, edges.csv).
2) Category taxonomy v0:
   - Seed mapping for frequent categories; queue long tail for LLM classification; commit mapping table.

Week 2 – Neo4j build
3) Stand up Neo4j 5.x; apply constraints/indexes.
4) Load nodes/edges from `exports/` with `LOAD CSV`.
5) Create NEARBY edges for BusinessLocation within 1–3 miles (batch with APOC and spatial filter).

Week 3 – Scoring MVP
6) Implement feature computation per block group (competition density, income fit, demographic fit, traffic proxies).
7) Implement `recommend(bg|zip|community, brand)` Cypher that returns top‑k with feature breakdown.
8) Notebook delivering first brand runs (e.g., coffee chains) and sanity checks.

Week 4 – LLM assist and UX
9) Explanations: write a retriever (Cypher → JSON facts) + prompt template that produces concise, grounded rationales.
10) Optional Streamlit app: brand selector, weight sliders, map, and export button.

## 12) What We’ll Likely Need Next

- Enrichment candidates: POI data beyond Google categories, mobile foot traffic, rent/lease comps, zoning.
- Better category ontology: NAICS/brand‑specific hierarchies and similarity matrix.
- Multi‑county expansion: ingest countyfp beyond 73 and test composite keys.
- Backtesting data: historical openings to tune weights and calibrate thresholds.

## 13) Example Artifacts to Add

- `scripts/cleanse.py` – implements all hygiene steps and exports CSVs.
- `scripts/load_neo4j.cypher` – constraints + LOAD CSV commands.
- `notebooks/FranchisePlanner_MVP.ipynb` – runs per‑brand recommendation and prints top‑k with explanations.
- `services/app.py` – Streamlit prototype.

---

Next steps: implement `scripts/cleanse.py`, export CSV schemas, and a `load_neo4j.cypher` starter to accelerate loading and testing.

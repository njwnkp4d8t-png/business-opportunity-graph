# Business Opportunity Knowledge Graph – Franchise Planner
UCSD DSE 203 Project

The idea is simple: help a planner answer “Where should we open next?” with data, not vibes. We blend points (business locations) and polygons (block groups, cities, etc.) into a graph, add a few smart features, and rank promising regions. A dash of explanation makes it shareable.

## 🎯 Goal
Pick the best areas to open a new location for a given brand in San Diego + Imperial counties, with explainable reasons.

## 🧠 Approach (high‑level)
- Clean and normalize data (categories, community names, IDs). Key block groups by 12‑digit GEOID to avoid county collisions.
- Use PostGIS for spatial truth (point‑in‑polygon, nearest fallbacks, centroids) and ESRI enrichments.
- Load into Neo4j for fast traversals and explainable retrieval (e.g., competition, adjacency, containment).
- Score regions with interpretable features (income, population, traffic proxies, competition, cannibalization) and generate human‑readable explanations.

## 🧩 Entities (Nodes)
- Business (brand‑level)
- BusinessLocation (store instance)
- State, County, City, Community, Zipcode
- BlockGroup (keyed by GEOID, with ctblockgroup as a property)

## 🔗 Relationships (Edges)
- CONTAINED_IN: City→County→State; Community→City; Location→{BlockGroup, Zipcode, City}
- ADJACENT_TO / NEARBY: between places or locations (distance‑based)
- OVERLAPS_WITH: Community↔BlockGroup/Zipcode (when derived from geometry)

## 🛠️ Stack
- PostGIS for spatial ops and authoritative joins
- Python + Pandas for ETL
- Neo4j (+ APOC) for graph queries
- Optional Streamlit for a quick UI

## 🚦 What’s implemented here
- Dual‑county scope (San Diego + Imperial) with GEOID as the BlockGroup key
- JSON→CSV exports with category + community normalization hooks
- PostGIS loaders and spatial assignments (PIP + nearest fallback)
- ESRI enrichment hook (plug in your ESRI tables and run)
- Neo4j CSV load (constraints, nodes, edges, NEARBY)
- A tiny scoring notebook and a minimal Streamlit app that ranks regions from CSVs

## ▶️ Running the pipeline (easy mode)
- One‑command runner: `python -m scripts.implementation1 --mode quick` (CSV only) or `--mode postgis` (full spatial route). See `docs/implementation1_runner_guide.md` for flags and options.
- Streamlit MVP: `streamlit run services/app.py` (expects `exports/` CSVs)

## 📈 Scoring (MVP)
Start simple and keep it explainable:
`score = w_income*IncomeFit + w_pop*PopulationFit + w_proxy*TrafficProxies - w_penalty*BrandHere`
Tune weights, then add competition density and cannibalization once relationships are loaded.

## 🧹 Normalization (why it matters)
- Categories are messy. We map raw labels to a smaller canonical set so “coffee shop” looks like, well, a coffee shop.
- Community names show up in mixed case and styles. Alias mapping ties them back to real IDs so edges don’t get lost.

## 🧭 What’s left / next up
- Expand category and community lookup coverage (rules + batch mapping)
- Backfill/explain relationships in Neo4j (community overlaps, adjacency)
- Add cannibalization/competition features and explanatory snippets
- Optional: drive‑time catchments (isochrones) and mobile foot traffic

Have fun poking around, and if something looks off, it probably needs a tiny nudge (or a bigger coffee).

---

More docs:
- Detailed plan: `docs/plan_detailed_franchise_planner.md`
- Parallel plan: `docs/plan_parallel_execution.md`
- Changes implemented: `docs/changes_implemented_summary.md`
- Implementation runner guide: `docs/implementation1_runner_guide.md`
- Potential issues and mitigations: `docs/potential_issues_and_mitigations.md`

Note: If `franchise_likelihood_filtered.csv` is present at repo root, exports will include a `franchise_likelihood` score per location/business based on category mapping.

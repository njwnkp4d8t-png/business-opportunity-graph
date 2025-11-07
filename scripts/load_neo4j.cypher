// Neo4j load script: create constraints and load CSV exports.
// Copy exports/*.csv into Neo4j's import directory (e.g., ./neo4j/import/).

// Constraints and indexes
CREATE CONSTRAINT city_name IF NOT EXISTS FOR (n:City) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT county_name IF NOT EXISTS FOR (n:County) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT community_name IF NOT EXISTS FOR (n:Community) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT zipcode_zip IF NOT EXISTS FOR (n:Zipcode) REQUIRE n.zip IS UNIQUE;
// Use GEOID for uniqueness across counties
CREATE CONSTRAINT blockgroup_geoid IF NOT EXISTS FOR (n:BlockGroup) REQUIRE n.geoid IS UNIQUE;
CREATE CONSTRAINT business_name IF NOT EXISTS FOR (n:Business) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:BusinessLocation) REQUIRE n.id IS UNIQUE;
CREATE INDEX location_point IF NOT EXISTS FOR (n:BusinessLocation) ON (n.geom);

// Load places
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///states.csv' AS row
MERGE (:State {id: toInteger(row.id), code: row.code, name: row.name});

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///counties.csv' AS row
MERGE (:County {id: toInteger(row.id), name: row.name});

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///cities.csv' AS row
MERGE (:City {id: toInteger(row.id), name: row.name});

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///communities.csv' AS row
MERGE (:Community {id: toInteger(row.id), name: row.name});

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///zipcodes.csv' AS row
MERGE (:Zipcode {zip: row.zip});

// BlockGroups with properties and centroids
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///blockgroups.csv' AS row
MERGE (bg:BlockGroup {geoid: row.geoid})
SET bg.medhinc_cy = CASE WHEN row.medhinc_cy = '' THEN NULL ELSE toInteger(row.medhinc_cy) END,
    bg.avghinc_cy = CASE WHEN row.avghinc_cy = '' THEN NULL ELSE toInteger(row.avghinc_cy) END,
    bg.gini_fy    = CASE WHEN row.gini_fy = '' THEN NULL ELSE toFloat(row.gini_fy) END,
    bg.totpop_cy  = CASE WHEN row.totpop_cy = '' THEN NULL ELSE toInteger(row.totpop_cy) END,
    bg.n01_bus    = CASE WHEN row.n01_bus = '' THEN NULL ELSE toFloat(row.n01_bus) END,
    bg.s23_emp    = CASE WHEN row.s23_emp = '' THEN NULL ELSE toFloat(row.s23_emp) END,
    bg.n37_sales  = CASE WHEN row.n37_sales = '' THEN NULL ELSE toFloat(row.n37_sales) END,
    bg.centroid   = CASE WHEN row.centroid_lon = '' OR row.centroid_lat = '' THEN NULL ELSE point({longitude: toFloat(row.centroid_lon), latitude: toFloat(row.centroid_lat)}) END,
    bg.ctblockgroup = CASE WHEN row.ctblockgroup = '' THEN NULL ELSE toInteger(row.ctblockgroup) END;

// Business nodes (brand-level)
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///businesses.csv' AS row
MERGE (b:Business {name: row.name})
SET b.num_locations = toInteger(row.num_locations),
    b.categories    = CASE WHEN row.categories = '' THEN [] ELSE split(row.categories,'|') END;

// BusinessLocation nodes
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///locations.csv' AS row
MERGE (loc:BusinessLocation {id: toInteger(row.id)})
SET loc.name       = row.name,
    loc.avg_rating = CASE WHEN row.avg_rating = '' THEN NULL ELSE toFloat(row.avg_rating) END,
    loc.franchise  = row.franchise,
    loc.confidence = CASE WHEN row.confidence = '' THEN NULL ELSE toFloat(row.confidence) END,
    loc.categories = CASE WHEN row.categories = '' THEN [] ELSE split(row.categories,'|') END,
    loc.geom       = point({longitude: toFloat(row.longitude), latitude: toFloat(row.latitude)});

// Containment edges: Location -> BlockGroup
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///loc_bg.csv' AS row
MATCH (loc:BusinessLocation {id: toInteger(row.id)})
// Prefer geoid if provided; else fallback to ctblockgroup property on bg
FOREACH (_ IN CASE WHEN row.bg_geoid IS NOT NULL AND row.bg_geoid <> '' THEN [1] ELSE [] END |
  MERGE (bg1:BlockGroup {geoid: row.bg_geoid})
  MERGE (loc)-[:CONTAINED_IN]->(bg1)
)
FOREACH (_ IN CASE WHEN (row.bg_geoid IS NULL OR row.bg_geoid = '') AND row.ctblockgroup IS NOT NULL AND row.ctblockgroup <> '' THEN [1] ELSE [] END |
  MATCH (bg2:BlockGroup {ctblockgroup: toInteger(row.ctblockgroup)})
  MERGE (loc)-[:CONTAINED_IN]->(bg2)
);

// Optional containment edges: Location -> City, Location -> Zipcode
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///loc_city.csv' AS row
MATCH (loc:BusinessLocation {id: toInteger(row.id)})
MERGE (c:City {name: row.city})
MERGE (loc)-[:CONTAINED_IN]->(c);

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///loc_zip.csv' AS row
MATCH (loc:BusinessLocation {id: toInteger(row.id)})
MERGE (z:Zipcode {zip: row.zip})
MERGE (loc)-[:CONTAINED_IN]->(z);

// Create NEARBY edges within 3km (tunable). Requires APOC.
CALL apoc.periodic.iterate(
  "MATCH (a:BusinessLocation) RETURN a",
  "MATCH (b:BusinessLocation)
   WHERE id(a) < id(b) AND point.distance(a.geom,b.geom) < 3000
   MERGE (a)-[:NEARBY {meters: point.distance(a.geom,b.geom)}]->(b)",
  {batchSize: 1000, parallel: true}
);

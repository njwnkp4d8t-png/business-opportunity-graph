-- Export-ready feature views (PostGIS)

DROP MATERIALIZED VIEW IF EXISTS bg_features;
CREATE MATERIALIZED VIEW bg_features AS
SELECT
  bg.ctblockgroup,
  bg.medhinc_cy,
  bg.avghinc_cy,
  bg.totpop_cy,
  bg.n01_bus,
  bg.s23_emp,
  bg.n37_sales,
  ST_Y(ST_Centroid(bg.geom)) AS centroid_lat,
  ST_X(ST_Centroid(bg.geom)) AS centroid_lon,
  COUNT(bl.id) FILTER (WHERE bl.franchise = 'FRANCHISE') AS franchise_count,
  COUNT(bl.id) FILTER (WHERE bl.franchise = 'INDEPENDENT') AS independent_count,
  AVG(bl.avg_rating) AS avg_rating_loc
FROM block_groups bg
LEFT JOIN business_locations bl ON bl.ctblockgroup = bg.ctblockgroup
GROUP BY 1,2,3,4,5,6,7;

-- Example export commands (run in psql)
-- \copy (SELECT * FROM bg_features) TO 'exports/blockgroups.csv' CSV HEADER
-- \copy (SELECT id, name, avg_rating, franchise, confidence, ST_Y(geom) AS latitude, ST_X(geom) AS longitude, ctblockgroup FROM business_locations) TO 'exports/locations.csv' CSV HEADER


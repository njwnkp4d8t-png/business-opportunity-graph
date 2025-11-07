-- Spatial assignments and backfills in PostGIS

-- Null obvious bad points for re-geocoding
UPDATE business_locations
SET geom = NULL
WHERE ST_X(geom) > 180 OR ST_X(geom) < -180 OR ST_Y(geom) > 90 OR ST_Y(geom) < -90;

-- Assign BlockGroup via point-in-polygon
UPDATE business_locations bl
SET ctblockgroup = bg.ctblockgroup,
    geoid = bg.geoid
FROM block_groups bg
WHERE bl.geom IS NOT NULL AND ST_Contains(bg.geom, bl.geom);

-- Nearest centroid fallback when polygon containment fails
WITH missing AS (
  SELECT bl.id, bg.ctblockgroup, bg.geoid
  FROM business_locations bl
  JOIN LATERAL (
    SELECT ctblockgroup, geoid
    FROM block_groups
    ORDER BY ST_Centroid(geom) <-> bl.geom
    LIMIT 1
  ) bg ON TRUE
  WHERE bl.ctblockgroup IS NULL AND bl.geom IS NOT NULL
)
UPDATE business_locations bl
SET ctblockgroup = m.ctblockgroup,
    geoid = m.geoid
FROM missing m
WHERE bl.id = m.id;

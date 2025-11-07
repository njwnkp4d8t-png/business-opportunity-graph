-- Backfill admin tables from business_locations when JSON admin coverage is incomplete

-- Insert missing cities from business_locations
INSERT INTO cities (id, name)
SELECT DISTINCT
  abs(hashtext(coalesce(city,''))) % 1000000000 AS id,
  city AS name
FROM business_locations bl
LEFT JOIN cities c ON c.name = bl.city
WHERE bl.city IS NOT NULL AND bl.city <> '' AND c.id IS NULL;

-- Insert missing zipcodes from business_locations
INSERT INTO zipcodes (zip)
SELECT DISTINCT bl.zip
FROM business_locations bl
LEFT JOIN zipcodes z ON z.zip = bl.zip
WHERE bl.zip IS NOT NULL AND bl.zip <> '' AND z.zip IS NULL;


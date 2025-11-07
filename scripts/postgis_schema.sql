-- PostGIS schema and indexes for core tables
CREATE EXTENSION IF NOT EXISTS postgis;

-- Block Groups (MultiPolygon)
CREATE TABLE IF NOT EXISTS block_groups (
  geoid text PRIMARY KEY,
  ctblockgroup bigint,
  countyfp int,
  tractce int,
  blkgrpce int,
  medhinc_cy int,
  avghinc_cy int,
  gini_fy float8,
  totpop_cy int,
  n01_bus float8,
  s23_emp float8,
  n37_sales float8,
  di100_cy float8,
  di150_cy float8,
  geom geometry(MultiPolygon, 4326)
);

-- Business Locations (Point)
CREATE TABLE IF NOT EXISTS business_locations (
  id bigint PRIMARY KEY,
  name text,
  address text,
  city text,
  zip text,
  categories text[],
  avg_rating float8,
  franchise text,
  confidence float8,
  ctblockgroup bigint,
  geoid text,
  geom geometry(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_block_groups_geom ON block_groups USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_business_locations_geom ON business_locations USING GIST (geom);

-- Admin place tables
CREATE TABLE IF NOT EXISTS states (
  id int PRIMARY KEY,
  code text,
  name text
);

CREATE TABLE IF NOT EXISTS counties (
  id int PRIMARY KEY,
  name text
);

CREATE TABLE IF NOT EXISTS cities (
  id int PRIMARY KEY,
  name text
);

CREATE TABLE IF NOT EXISTS communities (
  id int PRIMARY KEY,
  name text
);

CREATE TABLE IF NOT EXISTS zipcodes (
  zip text PRIMARY KEY
);

-- Optional features view (recreated in export_views.sql for clarity)

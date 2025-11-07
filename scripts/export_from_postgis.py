"""
Export canonical CSVs for Neo4j directly from PostGIS after spatial assignments.

Writes to exports/: blockgroups.csv, locations.csv, businesses.csv, counties.csv, cities.csv,
communities.csv, zipcodes.csv, states.csv, loc_bg.csv, loc_city.csv, loc_zip.csv
"""

from __future__ import annotations

import os
import pathlib
import psycopg2
import csv

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "exports"


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "nourish"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
    )


def write_csv(path: pathlib.Path, headers: list[str], rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)


def main():
    EXPORT_DIR.mkdir(exist_ok=True)
    conn = connect()
    try:
        cur = conn.cursor()

        # Blockgroups from feature view if exists, else base table
        cur.execute("""
            SELECT
              bg.geoid,
              bg.ctblockgroup,
              COALESCE(f.centroid_lon, ST_X(ST_Centroid(bg.geom))) AS centroid_lon,
              COALESCE(f.centroid_lat, ST_Y(ST_Centroid(bg.geom))) AS centroid_lat,
              bg.medhinc_cy,
              bg.avghinc_cy,
              bg.gini_fy,
              bg.totpop_cy,
              bg.n01_bus, bg.s23_emp, bg.n37_sales
            FROM block_groups bg
            LEFT JOIN pg_matviews v ON v.matviewname = 'bg_features'
            LEFT JOIN bg_features f ON v.matviewname IS NOT NULL AND f.ctblockgroup = bg.ctblockgroup
        """)
        rows = cur.fetchall()
        write_csv(EXPORT_DIR / "blockgroups.csv",
                  ["geoid","ctblockgroup","centroid_lon","centroid_lat","medhinc_cy","avghinc_cy","gini_fy","totpop_cy","n01_bus","s23_emp","n37_sales"],
                  rows)

        # Locations
        cur.execute("""
            SELECT id, name,
                   avg_rating, franchise, confidence,
                   ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                   ctblockgroup,
                   geoid,
                   array_to_string(categories,'|') AS categories,
                   city, zip
            FROM business_locations
        """)
        rows = cur.fetchall()
        write_csv(EXPORT_DIR / "locations.csv",
                  ["id","name","avg_rating","franchise","confidence","latitude","longitude","blockgroup","geoid","categories"],
                  [(r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9]) for r in rows])

        # Businesses aggregated by name
        cur.execute("""
            SELECT name,
                   COUNT(*) AS num_locations,
                   array_to_string(ARRAY(SELECT DISTINCT unnest(categories)), '|') AS categories
            FROM business_locations
            GROUP BY name
        """)
        rows = cur.fetchall()
        write_csv(EXPORT_DIR / "businesses.csv",
                  ["name","num_locations","categories"], rows)

        # Admin tables
        for table, fname, headers in [
            ("states", "states.csv", ["id","code","name"]),
            ("counties","counties.csv", ["id","name"]),
            ("cities","cities.csv", ["id","name"]),
            ("communities","communities.csv", ["id","name"]),
            ("zipcodes","zipcodes.csv", ["zip"])]:
            cur.execute(f"SELECT {', '.join(headers)} FROM {table}")
            write_csv(EXPORT_DIR / fname, headers, cur.fetchall())

        # Relationship helpers
        cur.execute("SELECT id, geoid FROM business_locations WHERE geoid IS NOT NULL")
        write_csv(EXPORT_DIR / "loc_bg.csv", ["id","bg_geoid"], cur.fetchall())
        cur.execute("SELECT id, city FROM business_locations WHERE city IS NOT NULL AND city <> ''")
        write_csv(EXPORT_DIR / "loc_city.csv", ["id","city"], cur.fetchall())
        cur.execute("SELECT id, zip FROM business_locations WHERE zip IS NOT NULL AND zip <> ''")
        write_csv(EXPORT_DIR / "loc_zip.csv", ["id","zip"], cur.fetchall())

        print("Exported CSVs to exports/")
    finally:
        conn.close()


if __name__ == "__main__":
    main()


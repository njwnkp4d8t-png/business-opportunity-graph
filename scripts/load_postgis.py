"""
Load JSON data into PostGIS tables defined in postgis_schema.sql.

Environment variables:
  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

Usage:
  python -m scripts.load_postgis --limit 0  # 0 = all

Notes:
  - Inserts block_groups multipolygons from WKB hex in data/block_group.json
  - Inserts business_locations points from latitude/longitude in data/business_location.json
"""

from __future__ import annotations

import os
import pathlib
import argparse
import pandas as pd
import psycopg2
import psycopg2.extras

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def connect():
    dsn = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "nourish"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", "postgres"),
    }
    return psycopg2.connect(**dsn)


def load_block_groups(cur, limit: int = 0):
    df = pd.read_json(DATA_DIR / "block_group.json")

    # Prefer San Diego county if duplicates exist
    if "countyfp" in df.columns:
        df = df.sort_values(by=["ctblockgroup", "countyfp"], ascending=[True, False])
        df = df.drop_duplicates(subset=["ctblockgroup"], keep="first")

    cols = [
        "ctblockgroup", "countyfp", "tractce", "blkgrpce",
        "medhinc_cy", "avghinc_cy", "gini_fy", "totpop_cy",
        "n01_bus", "s23_emp", "n37_sales", "geom"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    if limit > 0:
        df = df.head(limit)

    sql = (
        "INSERT INTO block_groups (geoid, ctblockgroup, countyfp, tractce, blkgrpce, medhinc_cy, avghinc_cy, gini_fy, totpop_cy, n01_bus, s23_emp, n37_sales, geom)\n"
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, ST_SetSRID(ST_GeomFromWKB(%s), 4326))\n"
        "ON CONFLICT (geoid) DO UPDATE SET\n"
        "  ctblockgroup=EXCLUDED.ctblockgroup, countyfp=EXCLUDED.countyfp, tractce=EXCLUDED.tractce, blkgrpce=EXCLUDED.blkgrpce,\n"
        "  medhinc_cy=EXCLUDED.medhinc_cy, avghinc_cy=EXCLUDED.avghinc_cy, gini_fy=EXCLUDED.gini_fy, totpop_cy=EXCLUDED.totpop_cy,\n"
        "  n01_bus=EXCLUDED.n01_bus, s23_emp=EXCLUDED.s23_emp, n37_sales=EXCLUDED.n37_sales, geom=EXCLUDED.geom"
    )

    rows = 0
    for _, r in df.iterrows():
        wkb_hex = r.get("geom")
        wkb_bytes = bytes.fromhex(wkb_hex) if isinstance(wkb_hex, str) else None
        # Compute geoid if possible
        try:
            s = int(r.get("statefp"))
            c = int(r.get("countyfp"))
            t = int(r.get("tractce"))
            b = int(r.get("blkgrpce"))
            geoid = f"{s:02d}{c:03d}{t:06d}{b:1d}"
        except Exception:
            geoid = None
        cur.execute(
            sql,
            (
                geoid,
                int(r["ctblockgroup"]) if pd.notna(r["ctblockgroup"]) else None,
                int(r["countyfp"]) if pd.notna(r["countyfp"]) else None,
                int(r["tractce"]) if pd.notna(r["tractce"]) else None,
                int(r["blkgrpce"]) if pd.notna(r["blkgrpce"]) else None,
                int(r["medhinc_cy"]) if pd.notna(r["medhinc_cy"]) else None,
                int(r["avghinc_cy"]) if pd.notna(r["avghinc_cy"]) else None,
                float(r["gini_fy"]) if pd.notna(r["gini_fy"]) else None,
                int(r["totpop_cy"]) if pd.notna(r["totpop_cy"]) else None,
                float(r["n01_bus"]) if pd.notna(r["n01_bus"]) else None,
                float(r["s23_emp"]) if pd.notna(r["s23_emp"]) else None,
                float(r["n37_sales"]) if pd.notna(r["n37_sales"]) else None,
                psycopg2.Binary(wkb_bytes),
            ),
        )
        rows += 1
    return rows


def load_business_locations(cur, limit: int = 0):
    df = pd.read_json(DATA_DIR / "business_location.json")

    # Bounding box filter for SD area
    lat_ok = df["latitude"].between(32.0, 34.0)
    lon_ok = df["longitude"].between(-125.0, -114.0)
    df = df[lat_ok & lon_ok].copy()

    # Cast blockgroup to integer where present
    df["blockgroup"] = df["blockgroup"].apply(lambda x: int(x) if pd.notna(x) else None)

    if limit > 0:
        df = df.head(limit)

    sql = (
        "INSERT INTO business_locations (id, name, address, city, zip, categories, avg_rating, franchise, confidence, ctblockgroup, geoid, geom)\n"
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))\n"
        "ON CONFLICT (id) DO UPDATE SET\n"
        "  name=EXCLUDED.name, address=EXCLUDED.address, city=EXCLUDED.city, zip=EXCLUDED.zip, categories=EXCLUDED.categories,\n"
        "  avg_rating=EXCLUDED.avg_rating, franchise=EXCLUDED.franchise, confidence=EXCLUDED.confidence, ctblockgroup=EXCLUDED.ctblockgroup, geoid=EXCLUDED.geoid, geom=EXCLUDED.geom"
    )

    rows = 0
    for _, r in df.iterrows():
        cats = r.get("categories")
        if not isinstance(cats, list):
            cats = []
        cur.execute(
            sql,
            (
                int(r["id"]),
                r.get("name"),
                r.get("address"),
                r.get("city"),
                str(r.get("zip")) if pd.notna(r.get("zip")) else None,
                cats,
                float(r["avg_rating"]) if pd.notna(r.get("avg_rating")) else None,
                r.get("franchise"),
                float(r["confidence"]) if pd.notna(r.get("confidence")) else None,
                int(r.get("blockgroup")) if pd.notna(r.get("blockgroup")) else None,
                None,  # geoid set later by spatial assignment
                float(r.get("longitude")),
                float(r.get("latitude")),
            ),
        )
        rows += 1
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for quick tests (0=all)")
    args = parser.parse_args()

    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            n_bg = load_block_groups(cur, args.limit)
            n_bl = load_business_locations(cur, args.limit)
        conn.commit()
        print(f"Inserted block_groups: {n_bg}")
        print(f"Inserted business_locations: {n_bl}")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

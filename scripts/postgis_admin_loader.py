"""
Load admin place tables (states, counties, cities, communities, zipcodes) into PostGIS.

Env:
  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
"""

from __future__ import annotations

import os
import pathlib
import pandas as pd
import psycopg2

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "nourish"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
    )


def upsert(cur, table: str, cols: list[str], rows: list[tuple], conflict: str):
    collist = ",".join(cols)
    placeholders = ",".join(["%s"] * len(cols))
    updates = ",".join([f"{c}=EXCLUDED.{c}" for c in cols if c != conflict])
    sql = f"INSERT INTO {table} ({collist}) VALUES ({placeholders}) ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
    for r in rows:
        cur.execute(sql, r)


def load_table_json(cur, json_name: str, table: str, mapping: dict[str, str], conflict: str):
    df = pd.read_json(DATA_DIR / json_name)
    df = df.rename(columns=mapping)
    cols = list(mapping.values())
    rows = [tuple(df[c].iloc[i] for c in cols) for i in range(len(df))]
    upsert(cur, table, cols, rows, conflict)


def main():
    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            load_table_json(cur, "state.json", "states", {"id": "id", "code": "code", "name": "name"}, "id")
            load_table_json(cur, "county.json", "counties", {"id": "id", "name": "name"}, "id")
            load_table_json(cur, "city.json", "cities", {"id": "id", "name": "name"}, "id")
            load_table_json(cur, "community.json", "communities", {"id": "id", "name": "name"}, "id")
            z = pd.read_json(DATA_DIR / "zipcode.json")
            if "zipcode" in z.columns:
                z = z.rename(columns={"zipcode": "zip"})
            rows = [(str(v),) for v in z["zip"].astype(str).tolist()]
            upsert(cur, "zipcodes", ["zip"], rows, "zip")
        conn.commit()
        print("Loaded admin tables: states, counties, cities, communities, zipcodes")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()


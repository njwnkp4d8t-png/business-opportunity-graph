"""
Cleanse and export CSVs for Neo4j/PostGIS loads.

Outputs: exports/*.csv
- blockgroups.csv: geoid, ctblockgroup, centroid_lon, centroid_lat, medhinc_cy, avghinc_cy, gini_fy, totpop_cy, n01_bus, s23_emp, n37_sales
- locations.csv: id, name, avg_rating, franchise, confidence, latitude, longitude, blockgroup, categories
- businesses.csv: name, num_locations, categories
- cities.csv: id, name
- counties.csv: id, name
- zipcodes.csv: zip
- communities.csv: id, name
- states.csv: id, code, name
- loc_bg.csv: id, ctblockgroup
- loc_city.csv: id, city
- loc_zip.csv: id, zip

Notes:
- This script performs light cleansing only. Spatial PIP backfills should be done in PostGIS using the provided SQL.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Iterable, Dict, Tuple

import pandas as pd

try:
    from shapely import wkb as shapely_wkb
except Exception:
    shapely_wkb = None  # Centroids will be left blank if Shapely is not available


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
EXPORT_DIR = REPO_ROOT / "exports"
LOOKUPS_DIR = REPO_ROOT / "lookups"


def load_json(name: str) -> pd.DataFrame:
    return pd.read_json(DATA_DIR / name)


def bbox_filter(df: pd.DataFrame, lat_col: str, lon_col: str,
                lat_min: float = 32.0, lat_max: float = 34.0,
                lon_min: float = -125.0, lon_max: float = -114.0) -> pd.DataFrame:
    m = (
        df[lat_col].between(lat_min, lat_max)
        & df[lon_col].between(lon_min, lon_max)
    )
    return df.loc[m].copy()


def to_centroid_lon_lat(hex_wkb: str | None) -> tuple[float | None, float | None]:
    if not hex_wkb or not shapely_wkb:
        return None, None
    try:
        geom = shapely_wkb.loads(bytes.fromhex(hex_wkb))
        c = geom.centroid
        return float(c.x), float(c.y)
    except Exception:
        return None, None


def make_geoid(row: pd.Series) -> str | None:
    try:
        s = int(row.get("statefp"))
        c = int(row.get("countyfp"))
        t = int(row.get("tractce"))
        b = int(row.get("blkgrpce"))
        return f"{s:02d}{c:03d}{t:06d}{b:1d}"
    except Exception:
        return None


def export_blockgroups() -> pd.DataFrame:
    bg = load_json("block_group.json")

    # Compute GEOID (12-digit) for uniqueness across SD (73) and Imperial (25)
    if {"statefp", "countyfp", "tractce", "blkgrpce"}.issubset(bg.columns):
        bg["geoid"] = bg.apply(make_geoid, axis=1)
    else:
        bg["geoid"] = None

    # Compute centroids if possible
    centroids = bg.get("geom")
    if centroids is not None:
        lons: list[Any] = []
        lats: list[Any] = []
        for g in centroids:
            lo, la = to_centroid_lon_lat(g)
            lons.append(lo)
            lats.append(la)
        bg["centroid_lon"] = lons
        bg["centroid_lat"] = lats
    else:
        bg["centroid_lon"] = None
        bg["centroid_lat"] = None

    cols_keep = [
        "geoid", "ctblockgroup", "centroid_lon", "centroid_lat",
        "medhinc_cy", "avghinc_cy", "gini_fy", "totpop_cy",
        "n01_bus", "s23_emp", "n37_sales",
    ]
    for c in cols_keep:
        if c not in bg.columns:
            bg[c] = None

    out = bg[cols_keep].copy()
    # Casts
    out["ctblockgroup"] = pd.to_numeric(out["ctblockgroup"], errors="coerce").astype("Int64")

    EXPORT_DIR.mkdir(exist_ok=True)
    out.to_csv(EXPORT_DIR / "blockgroups.csv", index=False)
    return out


def load_category_map() -> Dict[str, Tuple[str, float]]:
    path = LOOKUPS_DIR / "category_map.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    out: Dict[str, Tuple[str, float]] = {}
    for _, r in df.iterrows():
        raw = str(r.get("raw_category", "")).strip().lower()
        canon = str(r.get("canonical_category", "")).strip()
        conf = float(r.get("confidence", 1.0)) if pd.notna(r.get("confidence")) else 1.0
        if raw:
            out[raw] = (canon, conf)
    return out


def map_categories(raw: Any, cmap: Dict[str, Tuple[str, float]]) -> list[str]:
    if not isinstance(raw, list):
        return []
    res: list[str] = []
    seen = set()
    for cat in raw:
        key = str(cat).strip().lower()
        canon = cmap.get(key, (cat, 1.0))[0]
        canon_s = str(canon)
        if canon_s not in seen and canon_s:
            res.append(canon_s)
            seen.add(canon_s)
    return res


def export_locations() -> pd.DataFrame:
    loc = load_json("business_location.json")
    cat_map = load_category_map()

    # Fix blockgroup data types
    if "blockgroup" in loc.columns:
        loc["blockgroup"] = loc["blockgroup"].apply(lambda x: int(x) if pd.notna(x) else None)

    # Drop egregious geocode errors using a SD bounding box
    loc = bbox_filter(loc, lat_col="latitude", lon_col="longitude")

    # Flatten categories to pipe-delimited for CSV
    def join_cats(x: Any) -> str:
        if isinstance(x, list):
            return "|".join(map(str, x))
        return ""

    # Best-effort mapping ctblockgroup -> geoid using unique mapping in BG table
    bg = load_json("block_group.json")
    if {"statefp", "countyfp", "tractce", "blkgrpce"}.issubset(bg.columns):
        bg["geoid"] = bg.apply(make_geoid, axis=1)
    # Build mapping for ctblockgroup -> geoid only if one-to-one; else None
    ct_to_geoid = (
        bg.groupby("ctblockgroup")["geoid"]
        .agg(lambda s: s.iloc[0] if s.nunique() == 1 else None)
        .to_dict()
        if "ctblockgroup" in bg.columns and "geoid" in bg.columns else {}
    )

    out = loc[[
        "id", "name", "avg_rating", "franchise", "confidence",
        "latitude", "longitude", "blockgroup", "city", "zip"
    ]].copy()
    # Map categories to canonical
    out["categories"] = loc["categories"].apply(lambda xs: "|".join(map_categories(xs, cat_map)))
    # Keep raw categories for reference
    out["raw_categories"] = loc["categories"].apply(join_cats)

    # loc_bg edges with geoid when determinable from ctblockgroup
    loc_bg = out.loc[out["blockgroup"].notna(), ["id", "blockgroup"]].copy()
    loc_bg["geoid"] = loc_bg["blockgroup"].map(ct_to_geoid)

    EXPORT_DIR.mkdir(exist_ok=True)
    out[[
        "id", "name", "avg_rating", "franchise", "confidence",
        "latitude", "longitude", "blockgroup", "categories"
    ]].to_csv(EXPORT_DIR / "locations.csv", index=False)

    # Relationship helpers (prefer geoid if available)
    cols = ["id"]
    if "geoid" in loc_bg.columns:
        loc_bg.rename(columns={"geoid": "bg_geoid"}, inplace=True)
        cols.append("bg_geoid")
    loc_bg.rename(columns={"blockgroup": "ctblockgroup"}, inplace=True)
    cols.append("ctblockgroup")
    loc_bg[cols].to_csv(EXPORT_DIR / "loc_bg.csv", index=False)

    out[["id", "city"]].dropna().to_csv(EXPORT_DIR / "loc_city.csv", index=False)
    out[["id", "zip"]].dropna().to_csv(EXPORT_DIR / "loc_zip.csv", index=False)

    return out


def export_businesses() -> pd.DataFrame:
    biz = load_json("business.json")
    cat_map = load_category_map()

    def join_cats(x: Any) -> str:
        if isinstance(x, list):
            return "|".join(map(str, x))
        return ""

    out = biz[["name", "num_locations"]].copy()
    out["categories"] = biz["categories"].apply(lambda xs: "|".join(map_categories(xs, cat_map)))
    out["raw_categories"] = biz["categories"].apply(join_cats)
    out.to_csv(EXPORT_DIR / "businesses.csv", index=False)
    return out


def export_places() -> None:
    # State
    try:
        st = load_json("state.json")
        # Fix typo if present
        if "name" in st.columns:
            st["name"] = st["name"].replace({"Calfironia": "California"})
        st[["id", "code", "name"]].to_csv(EXPORT_DIR / "states.csv", index=False)
    except Exception:
        pass

    # County, City, Community, Zipcodes
    try:
        load_json("county.json")[ ["id", "name"] ].to_csv(EXPORT_DIR / "counties.csv", index=False)
    except Exception:
        pass
    try:
        load_json("city.json")[ ["id", "name"] ].to_csv(EXPORT_DIR / "cities.csv", index=False)
    except Exception:
        pass
    try:
        load_json("community.json")[ ["id", "name"] ].to_csv(EXPORT_DIR / "communities.csv", index=False)
    except Exception:
        pass
    try:
        z = load_json("zipcode.json")
        # Normalize column to 'zip'
        if "zipcode" in z.columns and "zip" not in z.columns:
            z = z.rename(columns={"zipcode": "zip"})
        (z[["zip"]].astype(str).drop_duplicates()).to_csv(EXPORT_DIR / "zipcodes.csv", index=False)
    except Exception:
        pass


def normalize_communities_and_export_relationships() -> None:
    # Load lookups
    aliases: Dict[str, Any] = {}
    if (LOOKUPS_DIR / "communities_aliases.csv").exists():
        df_alias = pd.read_csv(LOOKUPS_DIR / "communities_aliases.csv")
        for _, r in df_alias.iterrows():
            alias = str(r.get("alias", "")).strip().upper()
            cid = r.get("canonical_id")
            if alias:
                aliases[alias] = cid
    # Build name->id map from community.json
    comm = load_json("community.json") if (DATA_DIR / "community.json").exists() else pd.DataFrame()
    name_to_id = {}
    if not comm.empty:
        for _, r in comm.iterrows():
            name_to_id[str(r["name"]).strip().upper()] = r["id"]

    # Blockgroup mapping ctblockgroup -> geoid when unambiguous
    try:
        bg = load_json("block_group.json")
        bg["geoid"] = bg.apply(make_geoid, axis=1)
        ct_to_geoid = (
            bg.groupby("ctblockgroup")["geoid"]
            .agg(lambda s: s.iloc[0] if s.nunique() == 1 else None)
            .to_dict()
        )
    except Exception:
        ct_to_geoid = {}

    # Read relationships and normalize any community names
    rel_paths = [DATA_DIR / "relationships.json", DATA_DIR / "relationship.json"]
    frames = []
    for p in rel_paths:
        if p.exists():
            try:
                frames.append(pd.read_json(p))
            except Exception:
                pass
    if not frames:
        return
    rel = pd.concat(frames, ignore_index=True)

    def resolve_entity(val: Any, etype: str) -> Tuple[str | None, str]:
        t = (etype or "").strip().lower()
        # normalize
        if t in {"community", "community ", "communities"}:
            if pd.isna(val):
                return None, t
            if isinstance(val, (int, float)) and not pd.isna(val):
                return str(int(val)), "community_id"
            key = str(val).strip().upper()
            cid = aliases.get(key)
            if cid is not None and str(cid).strip() != "":
                return str(cid), "community_id"
            cid = name_to_id.get(key)
            if cid is not None:
                return str(cid), "community_id"
            return None, "community_unknown"
        if t in {"city", "city ", "cities"}:
            # map by name
            if isinstance(val, (int, float)) and not pd.isna(val):
                return str(int(val)), "city_id"
            key = str(val).strip().upper()
            # Try exact name match
            for nm, cid in name_to_id.items():
                if nm == key:
                    return str(cid), "city_id"
            return None, "city_unknown"
        if t in {"blockgroup", "block group", "block_group"}:
            try:
                ct = int(val)
            except Exception:
                return None, "blockgroup_unknown"
            geoid = ct_to_geoid.get(ct)
            return (geoid if geoid else str(ct)), ("geoid" if geoid else "ctblockgroup")
        if t in {"zipcode", "zip", "zip code"}:
            return (str(val) if not pd.isna(val) else None), "zip"
        if t in {"county"}:
            # We don't create ids for counties from names here
            return (str(val) if not pd.isna(val) else None), "county"
        if t in {"business", "business location", "business_location"}:
            try:
                return str(int(val)), "business_id"
            except Exception:
                return None, "business_unknown"
        return (str(val) if not pd.isna(val) else None), t

    rows = []
    for _, r in rel.iterrows():
        e1 = r.get("entity1")
        t1 = r.get("entitytype1")
        pred = r.get("predicate")
        e2 = r.get("entity2")
        t2 = r.get("entitytype2")
        res1, k1 = resolve_entity(e1, str(t1))
        res2, k2 = resolve_entity(e2, str(t2))
        rows.append({
            "entity1": e1,
            "entitytype1": t1,
            "predicate": pred,
            "entity2": e2,
            "entitytype2": t2,
            "entity1_resolved": res1,
            "entity1_kind": k1,
            "entity2_resolved": res2,
            "entity2_kind": k2,
        })

    df_out = pd.DataFrame(rows)
    df_out.to_csv(EXPORT_DIR / "relationships_mapped.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanse data and export CSVs for Neo4j/PostGIS")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    EXPORT_DIR.mkdir(exist_ok=True)

    bg = export_blockgroups()
    loc = export_locations()
    biz = export_businesses()
    export_places()
    normalize_communities_and_export_relationships()

    if args.verbose:
        print("Exported rows:")
        print("  blockgroups:", len(bg))
        print("  locations:", len(loc))
        print("  businesses:", len(biz))
        print("  loc_bg edges:", (EXPORT_DIR / "loc_bg.csv").exists())
        print("  relationships_mapped:", (EXPORT_DIR / "relationships_mapped.csv").exists())


if __name__ == "__main__":
    main()

import os
import pathlib
from typing import Optional

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

BASE = pathlib.Path(__file__).resolve().parents[1]
EXPORTS = BASE / "exports"

st.set_page_config(page_title="Franchise Planner", layout="wide")

# Simple CSS for a cleaner look
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem;}
    section[data-testid="stSidebar"] {width: 360px !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Franchise Planner")
st.caption("Rank Block Groups with interpretable features and quick filters.")


@st.cache_data(show_spinner=False)
def load_data():
    bg = pd.read_csv(EXPORTS / "blockgroups.csv") if (EXPORTS / "blockgroups.csv").exists() else None
    loc = pd.read_csv(EXPORTS / "locations.csv") if (EXPORTS / "locations.csv").exists() else None
    biz = pd.read_csv(EXPORTS / "businesses.csv") if (EXPORTS / "businesses.csv").exists() else None
    return bg, loc, biz


def pclip_norm(s: pd.Series, lo: float = 0.05, hi: float = 0.95) -> pd.Series:
    """Quantile clip then min-max normalize to reduce outlier effects."""
    if s is None or s.empty:
        return s
    a, b = s.quantile(lo), s.quantile(hi)
    s2 = s.clip(lower=a, upper=b)
    rng = s2.max() - s2.min()
    return (s2 - s2.min()) / rng if rng > 0 else s2 * 0


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance (km) between arrays of points and one point set."""
    R = 6371.0
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)
    dlat = lat2[:, None] - lat1[None, :]
    dlon = np.radians(lon2)[:, None] - np.radians(lon1)[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat2)[:, None] * np.cos(lat1)[None, :] * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c  # shape: (n_brand_points, n_bg)


bg, loc, biz = load_data()
if bg is None:
    st.warning("Missing exports/blockgroups.csv – run the pipeline first.")
    st.stop()

# Derive county fips from GEOID (digits 3-5)
if "geoid" in bg.columns:
    bg["countyfp"] = bg["geoid"].astype(str).str.slice(2, 5)
else:
    bg["countyfp"] = None

# Sidebar controls
with st.sidebar:
    st.header("Filters")
    county_choice = st.multiselect(
        "County",
        options=["073 – San Diego", "025 – Imperial"],
        default=["073 – San Diego", "025 – Imperial"],
    )
    county_map = {"073 – San Diego": "073", "025 – Imperial": "025"}
    county_fps = [county_map[c] for c in county_choice]

    brand = st.text_input("Brand (optional)", value="Starbucks", help="Exact brand filter is simple case-insensitive name search.")

    st.header("Weights")
    w_inc = st.slider("Income", 0.0, 1.0, 0.30, 0.05)
    w_pop = st.slider("Population", 0.0, 1.0, 0.30, 0.05)
    w_proxy = st.slider("Traffic proxies", 0.0, 1.0, 0.30, 0.05)
    w_like = st.slider("Franchise likelihood", 0.0, 1.0, 0.10, 0.05)
    w_cann = st.slider("Cannibalization penalty", 0.0, 1.0, 0.15, 0.05, help="Penalty increases as nearest same-brand gets closer.")
    topn = st.number_input("Top N", 1, 500, 100)


# Prepare features
df = bg.copy()
for c in ["medhinc_cy", "totpop_cy", "n01_bus", "s23_emp", "n37_sales", "centroid_lat", "centroid_lon"]:
    if c not in df.columns:
        df[c] = np.nan

df["inc_fit"] = pclip_norm(df["medhinc_cy"])  # income
df["pop_fit"] = pclip_norm(df["totpop_cy"])   # population
df["proxy_fit"] = pclip_norm(df[["n01_bus", "s23_emp", "n37_sales"]].fillna(0).sum(axis=1))

# Aggregate franchise likelihood over locations per block group (average)
like_bg = None
if loc is not None and "franchise_likelihood" in loc.columns:
    tmp = loc.dropna(subset=["blockgroup"])
    if not tmp.empty:
        like_bg = tmp.groupby("blockgroup")["franchise_likelihood"].mean().rename("like_fit")
        df = df.merge(like_bg, left_on="ctblockgroup", right_index=True, how="left")
        df["like_fit"].fillna(0.0, inplace=True)
    else:
        df["like_fit"] = 0.0
else:
    df["like_fit"] = 0.0

# County filter
if county_fps:
    df = df[df["countyfp"].isin(county_fps)]

# Cannibalization: distance to nearest same-brand location (km)
df["brand_km"] = np.nan
if loc is not None and brand:
    brand_locs = loc[loc["name"].str.contains(brand, case=False, na=False)] if "name" in loc.columns else pd.DataFrame()
    if not brand_locs.empty and df["centroid_lat"].notna().any() and df["centroid_lon"].notna().any():
        b_lat = brand_locs["latitude"].to_numpy(dtype=float)
        b_lon = brand_locs["longitude"].to_numpy(dtype=float)
        g_lat = df["centroid_lat"].fillna(0).to_numpy(dtype=float)
        g_lon = df["centroid_lon"].fillna(0).to_numpy(dtype=float)
        if b_lat.size and g_lat.size:
            D = haversine_km(g_lat, g_lon, b_lat, b_lon)  # shape (n_brand, n_bg)
            min_km = np.min(D, axis=0)
            df["brand_km"] = min_km

# Penalty: map distance to [0..1] penalty (0 if far, 1 if very close). 3km knee by default
def penalty_from_km(s: pd.Series, knee_km: float = 3.0) -> pd.Series:
    x = s.copy()
    x = x.fillna(x.max() if not x.dropna().empty else 0)
    pen = 1.0 - (x / knee_km)
    pen = pen.clip(lower=0.0, upper=1.0)
    return pen

df["cann_pen"] = penalty_from_km(df["brand_km"]) if brand else 0.0

# Final score
df["score"] = (
    w_inc * df["inc_fit"].fillna(0)
    + w_pop * df["pop_fit"].fillna(0)
    + w_proxy * df["proxy_fit"].fillna(0)
    + w_like * df["like_fit"].fillna(0)
    - w_cann * df["cann_pen"].fillna(0)
)

df_sorted = df.sort_values("score", ascending=False)

tab1, tab2, tab3 = st.tabs(["Leaderboard", "Map", "Diagnostics"])

with tab1:
    st.subheader("Top Candidates")
    show_cols = [c for c in ["geoid", "ctblockgroup", "medhinc_cy", "totpop_cy", "inc_fit", "pop_fit", "proxy_fit", "like_fit", "brand_km", "cann_pen", "score"] if c in df_sorted.columns]
    st.dataframe(df_sorted[show_cols].head(int(topn)), use_container_width=True)
    csv = df_sorted.head(int(topn)).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, file_name="franchise_planner_topN.csv", mime="text/csv")

with tab2:
    st.subheader("Map")
    if {"centroid_lat", "centroid_lon"}.issubset(df_sorted.columns):
        # Normalize scores for color scale
        s_norm = pclip_norm(df_sorted["score"]).fillna(0)
        map_df = df_sorted[["geoid", "ctblockgroup", "centroid_lat", "centroid_lon", "score"]].copy()
        map_df["norm"] = s_norm
        layer_bg = pdk.Layer(
            "ScatterplotLayer",
            data=map_df.head(1000),
            get_position="[centroid_lon, centroid_lat]",
            get_radius= "(norm + 0.1) * 800",
            get_fill_color="[255 * (1-norm), 120 * norm, 180, 160]",
            pickable=True,
        )
        layers = [layer_bg]
        # Overlay brand locations if present
        if loc is not None and brand:
            brand_locs = loc[loc["name"].str.contains(brand, case=False, na=False)] if "name" in loc.columns else pd.DataFrame()
            if not brand_locs.empty:
                layer_brand = pdk.Layer(
                    "ScatterplotLayer",
                    data=brand_locs,
                    get_position="[longitude, latitude]",
                    get_radius=100,
                    get_fill_color=[255, 80, 60, 200],
                    pickable=True,
                )
                layers.append(layer_brand)
        view_state = pdk.ViewState(latitude=32.8, longitude=-117.1, zoom=9.5)
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "BG {ctblockgroup}\nScore: {score}"}))
    else:
        st.info("Centroids not available in blockgroups.csv; run the full export to add them.")

with tab3:
    st.subheader("Diagnostics")
    st.write("Rows:", len(df_sorted))
    st.write("Score min/max:", float(df_sorted["score"].min()), float(df_sorted["score"].max()))
    if loc is not None and brand:
        st.write("Brand locations found:", int((loc["name"].str.contains(brand, case=False, na=False)).sum()))


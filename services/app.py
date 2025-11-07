import os
import pathlib
import pandas as pd
import streamlit as st

BASE = pathlib.Path(__file__).resolve().parents[1]
EXPORTS = BASE / "exports"

st.set_page_config(page_title="Franchise Planner MVP", layout="wide")
st.title("Franchise Planner – Tiny MVP")
st.caption("Loads exported CSVs and ranks Block Groups with a simple score.")

@st.cache_data
def load_data():
    bg = pd.read_csv(EXPORTS / "blockgroups.csv") if (EXPORTS / "blockgroups.csv").exists() else None
    loc = pd.read_csv(EXPORTS / "locations.csv") if (EXPORTS / "locations.csv").exists() else None
    biz = pd.read_csv(EXPORTS / "businesses.csv") if (EXPORTS / "businesses.csv").exists() else None
    return bg, loc, biz

bg, loc, biz = load_data()

if bg is None:
    st.warning("Missing exports/blockgroups.csv – run the pipeline first.")
    st.stop()

brand = st.text_input("Brand (optional)", value="Starbucks")
col1, col2, col3, col4 = st.columns(4)
with col1:
    w_inc = st.slider("Income weight", 0.0, 1.0, 0.3, 0.05)
with col2:
    w_pop = st.slider("Population weight", 0.0, 1.0, 0.3, 0.05)
with col3:
    w_proxy = st.slider("Traffic proxy weight", 0.0, 1.0, 0.3, 0.05)
with col4:
    w_pen = st.slider("Penalty (brand here)", 0.0, 1.0, 0.1, 0.05)

df = bg.copy()
for c in ["medhinc_cy", "totpop_cy", "n01_bus", "s23_emp", "n37_sales"]:
    if c not in df.columns:
        df[c] = 0

# Normalize to ~0..1 (avoid divide by zero)
norm = lambda s: (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0
df["inc_fit"] = norm(df["medhinc_cy"])
df["pop_fit"] = norm(df["totpop_cy"])
df["proxy_fit"] = norm(df[["n01_bus","s23_emp","n37_sales"]].fillna(0).sum(axis=1))

if loc is not None and brand:
    # Simple penalty if brand already exists in blockgroup
    present = (loc.dropna(subset=["blockgroup"]) if "blockgroup" in loc.columns else pd.DataFrame())
    if not present.empty:
        present["brand_here"] = present["name"].str.contains(brand, case=False, na=False)
        brand_ct = present.groupby("blockgroup")["brand_here"].any().astype(int)
        df = df.merge(brand_ct.rename("brand_here"), left_on="ctblockgroup", right_index=True, how="left")
        df["brand_here"].fillna(0, inplace=True)
    else:
        df["brand_here"] = 0
else:
    df["brand_here"] = 0

df["score"] = (
    w_inc * df["inc_fit"] +
    w_pop * df["pop_fit"] +
    w_proxy * df["proxy_fit"] -
    w_pen * df["brand_here"]
)

topn = st.number_input("Top N", 1, 200, 50)
st.subheader("Top Candidates")
st.dataframe(df.sort_values("score", ascending=False)[["geoid","ctblockgroup","medhinc_cy","totpop_cy","score"]].head(int(topn)))

st.caption("This is a lightweight MVP; the full planner uses Neo4j relationships and richer features.")


"""Washington EV Explorer: transparent metrics from a validated build."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Washington EV Explorer", page_icon="⚡", layout="wide")
st.title("⚡ Washington EV Explorer")
st.caption("Vehicle population • Model-year composition • Transparent data quality")
artifacts = Path(__file__).resolve().parent / "artifacts"
if not (artifacts / "current").exists():
    st.info("Build the demo first: uv run --locked python scripts/build.py")
    st.stop()
run = artifacts / (artifacts / "current").read_text().strip()
metadata = json.loads((run / "metadata.json").read_text())
if metadata["dataset"] == "synthetic sample":
    st.warning("SYNTHETIC DEMO — these invented records demonstrate the pipeline; they are not Washington statistics.")
st.caption(f"Dataset: {metadata['dataset']} · Built (UTC): {metadata['built_at']} · Build: {metadata['duration_seconds']} seconds")
vehicles = pd.read_csv(run / "enriched_electric_vehicles.csv")
quality = pd.read_csv(run / "data_quality.csv")
accepted = vehicles[vehicles.quality_status == "accepted"].copy()
accepted["county"] = accepted["county"].fillna("Unknown")
with st.sidebar:
    st.header("Explore the snapshot")
    makes = st.multiselect("Manufacturer", sorted(accepted.make.dropna().unique()))
    counties = st.multiselect("County", sorted(accepted.county.dropna().unique()))
    st.markdown("[Source dataset](https://catalog.data.gov/dataset/electric-vehicle-population-data)")
    st.caption("Model year is a vehicle attribute. It does not tell us when the vehicle was registered or purchased.")
filtered = accepted
if makes:
    filtered = filtered[filtered.make.isin(makes)]
if counties:
    filtered = filtered[filtered.county.isin(counties)]
a, b, c = st.columns(3)
a.metric("Vehicles in selection", f"{len(filtered):,}")
b.metric("Manufacturers", filtered.make.nunique())
c.metric("Counties represented", filtered.county.nunique())
if filtered.empty:
    st.info("No vehicles match these filters. Clear a manufacturer or county selection to explore again.")
if not filtered.empty:
    st.subheader("Which model years are represented?")
    st.caption("Counts within this snapshot, grouped by model year. This is not annual EV adoption.")
    st.bar_chart(filtered.groupby("model_year").size().rename("Vehicles"))
    left, right = st.columns(2)
    with left:
        st.subheader("Manufacturer mix")
        st.bar_chart(filtered.groupby("make").size().sort_values(ascending=False).rename("Vehicles"))
    with right:
        st.subheader("County distribution")
        st.bar_chart(filtered.groupby("county").size().sort_values(ascending=False).rename("Vehicles"))
    st.subheader("Vehicle locations")
    coordinates = filtered[["latitude", "longitude"]].dropna()
    coordinates = coordinates[coordinates.latitude.between(-90, 90) & coordinates.longitude.between(-180, 180)]
    if len(coordinates):
        st.map(coordinates)
    st.caption(f"{len(coordinates):,} of {len(filtered):,} selected records have usable coordinates. Locations are source-provided reference points, not exact vehicle positions.")
with st.expander("Data quality and metric definitions", expanded=True):
    st.write(f"Source: {len(vehicles):,} rows · Accepted: {len(accepted):,} · Excluded: {len(vehicles) - len(accepted):,}")
    st.dataframe(quality, hide_index=True, width="stretch")
    st.markdown("Acceptance requires a model year from 1900 through next year and a manufacturer. Missing location or range does not remove a vehicle. Zero or missing electric range is treated as unknown/not reported. Counts are source records; this projection cannot prove vehicle uniqueness. County totals are counts, not population-adjusted adoption rates.")
    st.caption("Quality totals refer to the whole source snapshot and do not change with filters.")
with st.expander("Explore and download the selection"):
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.download_button("Download selection", filtered.to_csv(index=False), "ev-selection.csv", "text/csv")

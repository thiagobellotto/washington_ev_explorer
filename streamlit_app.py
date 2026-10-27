import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Washington EV Explorer", page_icon=":material/electric_car:", layout="wide")
st.markdown("""
<style>
.stMainBlockContainer {max-width: 1440px; padding-top: 2rem; padding-bottom: 2rem;}
h1 {font-size: 2.2rem !important; letter-spacing: -.04em;}
h2 {font-size: 1.35rem !important; letter-spacing: -.02em;}
h3 {font-size: 1.05rem !important;}
[data-testid="stMetricValue"] {font-size: 1.85rem; font-variant-numeric: tabular-nums;}
[data-testid="stSidebar"] h1 {font-size: 1.2rem !important;}
@media (max-width: 640px) {.stMainBlockContainer {padding: 1rem;} h1 {font-size: 1.7rem !important;}}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parent
ACCENT = "#65D6B4"
BLUE = "#8EBDF3"


@st.cache_data(show_spinner="Loading vehicle records…", max_entries=2)
def load_snapshot(run_path):
    path = Path(run_path)
    frame = pd.read_csv(path / "enriched_electric_vehicles.csv")
    frame["county"] = frame["county"].fillna("Unknown")
    frame["state"] = frame["state"].fillna("Unknown")
    frame["model"] = frame["model"].fillna("Unknown")
    return frame, json.loads((path / "metadata.json").read_text())


def reset_filters():
    for key in ("makes", "counties", "years", "models", "search"):
        st.session_state.pop(key, None)


def clear_models():
    st.session_state.pop("models", None)


def date_label(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%b %d, %Y · %I:%M %p %Z")


def ranking(frame, column, label, color=ACCENT, limit=10):
    counts = frame.groupby(column).size().sort_values(ascending=False).head(limit).rename("Records").reset_index()
    counts = counts.rename(columns={column: label})
    counts["Share"] = counts.Records / len(frame)
    st.vega_lite_chart(counts, {
        "height": max(200, len(counts) * 28),
        "mark": {"type": "bar", "color": color, "cornerRadiusEnd": 3},
        "encoding": {
            "y": {"field": label, "type": "nominal", "sort": "-x", "axis": {"title": None, "labelLimit": 180}},
            "x": {"field": "Records", "type": "quantitative", "axis": {"title": None, "format": "~s", "tickCount": 4}},
            "tooltip": [{"field": label}, {"field": "Records", "format": ","}, {"field": "Share", "format": ".1%"}],
        },
        "config": {"view": {"stroke": None}, "axis": {"gridOpacity": .15, "domain": False}},
    }, width="stretch")
    return counts


pointer = ROOT / "artifacts/current"
if not pointer.exists():
    st.title("Washington EV Explorer")
    st.info("The dataset is being prepared. Start the app with docker compose up --build, then reload this page.")
    st.stop()
try:
    vehicles, metadata = load_snapshot(str(ROOT / "artifacts" / pointer.read_text().strip()))
except (OSError, ValueError, KeyError):
    st.error("This snapshot could not be loaded. Rebuild the pipeline, then reload this page.")
    st.stop()
accepted = vehicles[vehicles.quality_status == "accepted"].copy()
accepted["model_year"] = accepted.model_year.astype(int)
if accepted.empty:
    st.warning("No source records meet the data-quality rules. Refresh the source and rebuild the pipeline.")
    st.stop()

with st.sidebar:
    st.markdown("### EV Explorer")
    st.caption("WASHINGTON · VEHICLE POPULATION")
    st.divider()
    st.markdown("#### Filter the snapshot")
    geography = st.selectbox("Geographic scope", ["Washington", "All source records"], key="scope", on_change=reset_filters,
                             help="The source also contains records with addresses outside Washington.")
    scope = accepted[accepted.state == "WA"].copy() if geography == "Washington" else accepted.copy()
    scope["county_label"] = scope.county if geography == "Washington" else scope.county + " · " + scope.state
    min_year, max_year = int(accepted.model_year.min()), int(accepted.model_year.max())
    years = st.slider("Model year", min_year, max_year, (min_year, max_year), key="years")
    makes = st.multiselect("Manufacturer", sorted(scope.make.dropna().unique()), key="makes", placeholder="All manufacturers", on_change=clear_models)
    counties = st.multiselect("County", sorted(scope.county_label.unique()), key="counties", placeholder="All counties")
    with st.expander("Model filter"):
        model_scope = scope[scope.make.isin(makes)] if makes else scope
        models = st.multiselect("Model", sorted(model_scope.model.unique()), key="models", placeholder="All models")
    st.button("Reset filters", icon=":material/restart_alt:", on_click=reset_filters, width="stretch")
    st.divider()
    st.caption("SOURCE SNAPSHOT")
    st.markdown(f"**{len(vehicles):,} source records**")
    st.caption(f"Downloaded {date_label(metadata['downloaded_at'])}")
    st.link_button("Washington open data", "https://catalog.data.gov/dataset/electric-vehicle-population-data", icon=":material/open_in_new:", width="stretch")

filtered = scope[scope.model_year.between(*years)]
if makes:
    filtered = filtered[filtered.make.isin(makes)]
if counties:
    filtered = filtered[filtered.county_label.isin(counties)]
if models:
    filtered = filtered[filtered.model.isin(models)]

st.title("Washington EV Explorer")
st.caption("Explore the vehicles, manufacturers, and places shaping this snapshot.")
view = st.segmented_control("Explore view", ["Overview", "Geography", "Data & quality"], default="Overview", required=True, key="view", label_visibility="collapsed")
st.write("")
for column, label, value, help_text in zip(st.columns(4),
        ["Vehicle records", "Share of scope", "Manufacturers", "Counties"],
        [f"{len(filtered):,}", f"{len(filtered) / len(scope):.1%}" if len(scope) else "—", f"{filtered.make.nunique():,}", f"{filtered.county_label.nunique():,}"],
        ["Records matching the active filters.", "Selection as a share of accepted records in the geographic scope.", "Distinct manufacturers in the selection.", "Distinct county and state combinations in the selection."]):
    with column.container(border=True):
        st.metric(label, value, help=help_text)
filters_active = bool(makes or counties or models or years != (min_year, max_year))
st.caption(f"{geography} · Model years {years[0]}–{years[1]} · {'Filtered selection' if filters_active else 'All records in scope'}")

if filtered.empty:
    st.info("No records match this combination. Reset the filters or broaden the model-year range.")
    st.button("Show all records in scope", on_click=reset_filters, type="primary")
elif view == "Overview":
    with st.container(border=True):
        st.subheader("Model-year composition")
        st.caption("Vehicles grouped by their model year, within the current selection.")
        yearly = filtered.groupby("model_year").size().rename("Records").reset_index()
        st.vega_lite_chart(yearly, {
            "height": 220,
            "mark": {"type": "bar", "color": ACCENT, "cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3},
            "encoding": {
                "x": {"field": "model_year", "type": "ordinal", "axis": {"title": None, "labelAngle": -45}},
                "y": {"field": "Records", "type": "quantitative", "axis": {"title": None, "format": "~s", "tickCount": 4}},
                "tooltip": [{"field": "model_year", "title": "Model year"}, {"field": "Records", "format": ","}],
            },
            "config": {"view": {"stroke": None}, "axis": {"domain": False, "gridOpacity": .15}},
        }, width="stretch")
        st.caption("Model year is a vehicle attribute, not the year of purchase or registration.")
    left, right = st.columns(2)
    with left.container(border=True):
        st.subheader("Leading manufacturers")
        st.caption("Top 10 by record count")
        manufacturers = ranking(filtered, "make", "Manufacturer")
        with st.expander("View ranking data"):
            st.dataframe(manufacturers, hide_index=True, column_config={"Share": st.column_config.NumberColumn(format="percent")}, width="stretch")
    with right.container(border=True):
        st.subheader("Popular models")
        st.caption("Top 10 · manufacturer and model")
        model_data = filtered.assign(model_label=filtered.make + " " + filtered.model)
        model_counts = ranking(model_data, "model_label", "Model", BLUE)
        with st.expander("View ranking data"):
            st.dataframe(model_counts, hide_index=True, column_config={"Share": st.column_config.NumberColumn(format="percent")}, width="stretch")
    with st.expander("View model-year data"):
        st.dataframe(yearly.rename(columns={"model_year": "Model year"}), hide_index=True, width="stretch")

elif view == "Geography":
    left, right = st.columns([1.4, 1])
    with left.container(border=True):
        st.subheader("Where records are located")
        coords = filtered.loc[filtered.latitude.between(-90, 90) & filtered.longitude.between(-180, 180)]
        points = coords.groupby(["latitude", "longitude"]).size().rename("Records").reset_index()
        points["marker_size"] = 40 + points.Records.pow(.5) * 15
        if len(points):
            st.map(points, size="marker_size", color=ACCENT, height=420)
        else:
            st.info("No usable coordinates are available for this selection.")
        st.caption(f"{len(coords):,} of {len(filtered):,} records have usable coordinates. Marker size reflects records at a shared source reference point.")
    with right.container(border=True):
        st.subheader("Leading counties")
        st.caption("Top 10 by count · not population-adjusted")
        county_counts = ranking(filtered, "county_label", "County")
        with st.expander("View ranking data"):
            st.dataframe(county_counts, hide_index=True, column_config={"Share": st.column_config.NumberColumn(format="percent")}, width="stretch")

elif view == "Data & quality":
    st.subheader("Explore the records")
    search = st.text_input("Search within this selection", placeholder="Manufacturer, model or city", key="search")
    records = filtered
    if search.strip():
        searchable = filtered.make.str.cat(filtered.model, sep=" ").str.cat(filtered.city.fillna(""), sep=" ")
        records = filtered[searchable.str.contains(search.strip(), case=False, regex=False)]
    columns = {"model_year": "Model year", "make": "Manufacturer", "model": "Model", "county": "County", "city": "City", "state": "State", "electric_range": "Reported range (mi)", "range_category": "Range category"}
    export = records[list(columns)].rename(columns=columns)
    st.caption(f"{len(records):,} matching records · preview shows the first {min(len(records), 500):,}")
    st.dataframe(export.head(500), hide_index=True, width="stretch", height=360,
                 column_config={"Model year": st.column_config.NumberColumn(format="%d"), "Reported range (mi)": st.column_config.NumberColumn(format="%d")})
    st.download_button("Download matching records", data=lambda: export.to_csv(index=False).encode("utf-8"),
                       file_name="washington-ev-selection.csv", mime="text/csv", on_click="ignore", icon=":material/download:", disabled=export.empty)
    st.divider()
    st.subheader("Source quality")
    st.caption("These figures describe the full source snapshot, before geographic scope or filters.")
    total = len(vehicles)
    for column, label, value in zip(st.columns(3), ["Source records", "Accepted", "Excluded"], [total, len(accepted), total - len(accepted)]):
        column.metric(label, f"{value:,}")
    quality = vehicles.groupby("quality_status").size().rename("Records").reset_index()
    quality["quality_status"] = quality.quality_status.str.replace("_", " ").str.capitalize()
    st.dataframe(quality.rename(columns={"quality_status": "Status"}), hide_index=True, width="stretch")
    with st.expander("Definitions and source details"):
        st.markdown("Accepted records require a manufacturer and a model year from 1900 through next year. Missing county, location, or range does not exclude a record. Zero, negative, or missing range is treated as unreported. Counts are source records; a unique vehicle identifier is not retained.")
        st.markdown("The source includes out-of-state addresses. Washington scope uses the source State field. County totals are not population-adjusted, and locations are reference points rather than precise vehicle positions.")
        st.caption(f"Downloaded: {date_label(metadata['downloaded_at'])} · Built: {date_label(metadata['built_at'])} · Build duration: {metadata['duration_seconds']} s")

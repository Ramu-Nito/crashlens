"""crashlens dashboard — run with:  streamlit run app/dashboard.py"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# Make src/ importable when running via `streamlit run`
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crashlens import ask, config  # noqa: E402

st.set_page_config(page_title="crashlens — NYC Collision Analytics", layout="wide")


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    try:
        return con.execute("SELECT * FROM crashes").fetchdf()
    finally:
        con.close()


if not config.DUCKDB_PATH.exists():
    st.error("Warehouse not found. Run the pipeline first:  `python -m crashlens.pipeline`")
    st.stop()

df = load_data()

# ---------- Sidebar filters ----------
st.sidebar.title("crashlens")
st.sidebar.caption("NYC Motor Vehicle Collision Analytics")

boroughs = sorted(df["borough"].unique())
selected = st.sidebar.multiselect("Borough", boroughs, default=boroughs)
min_d, max_d = df["crash_datetime"].min().date(), df["crash_datetime"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)

mask = df["borough"].isin(selected)
if len(date_range) == 2:
    mask &= df["crash_datetime"].dt.date.between(*date_range)
view = df[mask]

# ---------- KPIs ----------
st.title("NYC Motor Vehicle Collisions")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Crashes", f"{len(view):,}")
c2.metric("People injured", f"{int(view['persons_injured'].sum()):,}")
c3.metric("People killed", f"{int(view['persons_killed'].sum()):,}")
c4.metric("Fatal crash rate", f"{view['is_fatal'].mean():.2%}" if len(view) else "—")

tab_trends, tab_factors, tab_map, tab_ask = st.tabs(
    ["📈 Trends", "🔍 Contributing Factors", "🗺️ Map", "🤖 Ask the Data"]
)

with tab_trends:
    monthly = view.groupby("crash_month").size().reset_index(name="crashes")
    st.plotly_chart(
        px.line(monthly, x="crash_month", y="crashes", title="Crashes per month"),
        use_container_width=True,
    )
    col_a, col_b = st.columns(2)
    hourly = view.groupby("crash_hour").size().reset_index(name="crashes")
    col_a.plotly_chart(
        px.bar(hourly, x="crash_hour", y="crashes", title="Crashes by hour of day"),
        use_container_width=True,
    )
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = view.groupby("day_of_week").size().reindex(dow_order).reset_index(name="crashes")
    col_b.plotly_chart(
        px.bar(dow, x="day_of_week", y="crashes", title="Crashes by day of week"),
        use_container_width=True,
    )

with tab_factors:
    factors = (
        view[view["contributing_factor"] != "Unspecified"]
        .groupby("contributing_factor")
        .agg(crashes=("collision_id", "count"), injuries=("persons_injured", "sum"))
        .nlargest(15, "crashes")
        .reset_index()
    )
    st.plotly_chart(
        px.bar(
            factors, x="crashes", y="contributing_factor", orientation="h",
            title="Top 15 contributing factors", hover_data=["injuries"],
        ).update_layout(yaxis={"categoryorder": "total ascending"}),
        use_container_width=True,
    )
    st.plotly_chart(
        px.bar(
            view.groupby("vehicle_type").size().nlargest(10).reset_index(name="crashes"),
            x="vehicle_type", y="crashes", title="Top 10 vehicle types involved",
        ),
        use_container_width=True,
    )

with tab_map:
    geo = view.dropna(subset=["latitude", "longitude"])
    fatal_only = st.checkbox("Fatal crashes only")
    if fatal_only:
        geo = geo[geo["is_fatal"]]
    sample = geo.sample(min(len(geo), 20_000), random_state=42) if len(geo) else geo
    st.caption(f"Showing {len(sample):,} of {len(geo):,} geocoded crashes")
    st.map(sample, latitude="latitude", longitude="longitude", size=10)

with tab_ask:
    st.subheader("Ask the data a question")
    st.caption("Powered by Claude — your question is converted to SQL and run on the local DuckDB warehouse.")
    if not ask.is_available():
        st.info(
            "Set the `ANTHROPIC_API_KEY` environment variable to enable AI querying.\n\n"
            "PowerShell:  `$env:ANTHROPIC_API_KEY = 'sk-ant-...'`  then restart the app."
        )
    else:
        question = st.text_input(
            "Question",
            placeholder="e.g. Which borough had the most cyclist injuries in 2024?",
        )
        if question:
            with st.spinner("Thinking..."):
                try:
                    result = ask.ask(question)
                except Exception as exc:  # surface API/SQL errors to the user
                    st.error(f"Could not answer that: {exc}")
                else:
                    st.markdown(f"**{result.explanation}**")
                    st.code(result.sql, language="sql")
                    st.dataframe(result.data, use_container_width=True)

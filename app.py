"""
app.py
-------
Bird Species Observation Analysis — Interactive Streamlit Dashboard

Analyzes bird species distribution and diversity across Forest and
Grassland habitats (National Park Service monitoring data), covering
temporal trends, spatial patterns, species diversity, environmental
correlations, distance/behavior, observer trends, and conservation
watchlist insights.

Run with:
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db_utils import load_data

# ==========================================================================
# Page config & light styling
# ==========================================================================
st.set_page_config(
    page_title="Bird Species Observation Analysis",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stMetric { background-color: rgba(46, 125, 50, 0.07); border-radius: 10px;
                padding: 12px 8px; }
    div[data-testid="stMetricValue"] { color: #2e7d32; }
    .habitat-badge { display:inline-block; padding: 2px 10px; border-radius: 12px;
                      font-size: 0.8rem; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]
MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
HABITAT_COLORS = {"Forest": "#2e7d32", "Grassland": "#c9a227"}

# ==========================================================================
# Load data
# ==========================================================================
try:
    df, source_label = load_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# ==========================================================================
# Sidebar — global filters
# ==========================================================================
st.sidebar.title("🐦 Filters")
st.sidebar.caption(f"Data source: **{source_label}**")

habitats = sorted(df["Location_Type"].dropna().unique().tolist())
sel_habitats = st.sidebar.multiselect("Habitat", habitats, default=habitats)

years = sorted(df["Year"].dropna().unique().tolist())
sel_years = st.sidebar.multiselect("Year", years, default=years)

species_options = sorted(df["Common_Name"].dropna().unique().tolist())
sel_species = st.sidebar.multiselect(
    "Species (leave empty = all)", species_options, default=[]
)

sex_options = sorted(df["Sex"].dropna().unique().tolist())
sel_sex = st.sidebar.multiselect("Sex", sex_options, default=sex_options)

observer_options = sorted(df["Observer"].dropna().unique().tolist())
sel_observers = st.sidebar.multiselect(
    "Observer (leave empty = all)", observer_options, default=[]
)

watchlist_only = st.sidebar.checkbox("PIF Watchlist species only", value=False)
flyover_only = st.sidebar.checkbox("Flyovers only", value=False)

min_date, max_date = df["Date"].min(), df["Date"].max()
if pd.notna(min_date) and pd.notna(max_date):
    date_range = st.sidebar.date_input(
        "Date range", value=(min_date.date(), max_date.date()),
        min_value=min_date.date(), max_value=max_date.date(),
    )
else:
    date_range = None

st.sidebar.markdown("---")
st.sidebar.caption(
    "Built for the **Bird Species Observation Analysis** project — "
    "Forest 🌲 vs Grassland 🌾 habitat comparison."
)

# ---- apply filters --------------------------------------------------------
f = df.copy()
if sel_habitats:
    f = f[f["Location_Type"].isin(sel_habitats)]
if sel_years:
    f = f[f["Year"].isin(sel_years)]
if sel_species:
    f = f[f["Common_Name"].isin(sel_species)]
if sel_sex:
    f = f[f["Sex"].isin(sel_sex)]
if sel_observers:
    f = f[f["Observer"].isin(sel_observers)]
if watchlist_only:
    f = f[f["PIF_Watchlist_Status"] == True]  # noqa: E712
if flyover_only:
    f = f[f["Flyover_Observed"] == True]  # noqa: E712
if date_range and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    f = f[(f["Date"] >= start) & (f["Date"] <= end)]

if f.empty:
    st.warning("No observations match the current filters. Try widening them in the sidebar.")
    st.stop()

# ==========================================================================
# Header + KPIs
# ==========================================================================
st.title("🐦 Bird Species Observation Analysis")
st.caption(
    "Distribution and diversity of bird species across **Forest** and "
    "**Grassland** ecosystems — habitat comparison, temporal & spatial "
    "patterns, environmental drivers, and conservation insights."
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Observations", f"{len(f):,}")
k2.metric("Unique Species", f"{f['Scientific_Name'].nunique():,}")
k3.metric("Sites Monitored", f"{f['Plot_Name'].nunique():,}")
k4.metric("Watchlist Species", f"{f.loc[f['PIF_Watchlist_Status'] == True, 'Common_Name'].nunique():,}")
k5.metric("Observers", f"{f['Observer'].nunique():,}")

st.markdown("---")

# ==========================================================================
# Tabs
# ==========================================================================
tab_overview, tab_temporal, tab_spatial, tab_species, tab_env, tab_behavior, \
    tab_observer, tab_conservation, tab_raw = st.tabs(
        [
            "📊 Overview", "📅 Temporal", "🗺️ Spatial", "🦉 Species",
            "🌦️ Environment", "📏 Distance & Behavior", "🧑‍🔬 Observers",
            "🛡️ Conservation", "📄 Raw Data",
        ]
    )

# --------------------------------------------------------------------------
# TAB 1 — Overview
# --------------------------------------------------------------------------
with tab_overview:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Observations by Habitat")
        habitat_counts = f["Location_Type"].value_counts().reset_index()
        habitat_counts.columns = ["Location_Type", "Observations"]
        fig = px.pie(
            habitat_counts, names="Location_Type", values="Observations", hole=0.45,
            color="Location_Type", color_discrete_map=HABITAT_COLORS,
        )
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Species Richness by Habitat")
        richness = f.groupby("Location_Type")["Scientific_Name"].nunique().reset_index()
        richness.columns = ["Location_Type", "Unique Species"]
        fig = px.bar(
            richness, x="Location_Type", y="Unique Species", color="Location_Type",
            color_discrete_map=HABITAT_COLORS, text="Unique Species",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 15 Most Frequently Observed Species")
    top_species = (
        f.groupby(["Common_Name", "Location_Type"]).size()
        .reset_index(name="Count")
    )
    top_names = f["Common_Name"].value_counts().head(15).index.tolist()
    top_species = top_species[top_species["Common_Name"].isin(top_names)]
    fig = px.bar(
        top_species, x="Count", y="Common_Name", color="Location_Type",
        color_discrete_map=HABITAT_COLORS, orientation="h",
        category_orders={"Common_Name": top_names[::-1]},
    )
    fig.update_layout(height=500, yaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 2 — Temporal Analysis
# --------------------------------------------------------------------------
with tab_temporal:
    st.subheader("Observations by Month")
    monthly = f.groupby(["Month_Name", "Location_Type"]).size().reset_index(name="Count")
    fig = px.bar(
        monthly, x="Month_Name", y="Count", color="Location_Type", barmode="group",
        category_orders={"Month_Name": MONTH_ORDER}, color_discrete_map=HABITAT_COLORS,
    )
    fig.update_layout(xaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Seasonal Trends")
        seasonal = f.groupby(["Season", "Location_Type"]).size().reset_index(name="Count")
        fig = px.bar(
            seasonal, x="Season", y="Count", color="Location_Type", barmode="group",
            category_orders={"Season": SEASON_ORDER}, color_discrete_map=HABITAT_COLORS,
        )
        fig.update_layout(legend_title="Habitat")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Observation Time Window")
        time_counts = f["Time_Of_Day"].value_counts().reset_index()
        time_counts.columns = ["Time_Of_Day", "Count"]
        fig = px.bar(time_counts, x="Time_Of_Day", y="Count", color="Time_Of_Day")
        fig.update_layout(showlegend=False, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Year × Month Activity Heatmap")
    heat = f.groupby(["Year", "Month_Name"]).size().reset_index(name="Count")
    if not heat.empty:
        pivot = heat.pivot(index="Year", columns="Month_Name", values="Count").reindex(
            columns=MONTH_ORDER
        )
        fig = px.imshow(
            pivot, aspect="auto", color_continuous_scale="YlGn",
            labels=dict(color="Observations"),
        )
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 3 — Spatial Analysis
# --------------------------------------------------------------------------
with tab_spatial:
    st.subheader("Observations by Site")
    site_counts = f.groupby(["Site_Name", "Location_Type"]).size().reset_index(name="Count")
    fig = px.bar(
        site_counts, x="Site_Name", y="Count", color="Location_Type",
        color_discrete_map=HABITAT_COLORS,
    )
    fig.update_layout(xaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 Plots by Species Richness (biodiversity hotspots)")
    plot_richness = (
        f.groupby(["Plot_Name", "Location_Type"])["Scientific_Name"]
        .nunique().reset_index(name="Unique Species")
        .sort_values("Unique Species", ascending=False).head(20)
    )
    fig = px.bar(
        plot_richness, x="Plot_Name", y="Unique Species", color="Location_Type",
        color_discrete_map=HABITAT_COLORS,
    )
    fig.update_layout(xaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "ℹ️ The source data doesn't include GPS coordinates, so plots/sites "
        "are compared by observation volume and species richness rather than "
        "a geographic map."
    )

# --------------------------------------------------------------------------
# TAB 4 — Species Analysis
# --------------------------------------------------------------------------
with tab_species:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Sex Ratio (all species)")
        sex_counts = f["Sex"].value_counts().reset_index()
        sex_counts.columns = ["Sex", "Count"]
        fig = px.pie(sex_counts, names="Sex", values="Count", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Identification Method")
        id_counts = f["ID_Method"].value_counts().reset_index()
        id_counts.columns = ["ID_Method", "Count"]
        fig = px.bar(id_counts, x="ID_Method", y="Count", color="ID_Method")
        fig.update_layout(showlegend=False, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Explore a Species")
    species_pick = st.selectbox(
        "Pick a species to inspect", sorted(f["Common_Name"].unique())
    )
    sp_df = f[f["Common_Name"] == species_pick]
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Observations", f"{len(sp_df):,}")
    sc2.metric("Sites", f"{sp_df['Plot_Name'].nunique():,}")
    sc3.metric("On Watchlist", "Yes ⚠️" if sp_df["PIF_Watchlist_Status"].any() else "No")
    sc4.metric("Scientific Name", sp_df["Scientific_Name"].iloc[0])

    cc1, cc2 = st.columns(2)
    with cc1:
        hab = sp_df["Location_Type"].value_counts().reset_index()
        hab.columns = ["Location_Type", "Count"]
        fig = px.bar(hab, x="Location_Type", y="Count", color="Location_Type",
                      color_discrete_map=HABITAT_COLORS)
        fig.update_layout(showlegend=False, title="Habitat preference")
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        mon = sp_df.groupby("Month_Name").size().reindex(MONTH_ORDER).dropna().reset_index(name="Count")
        fig = px.line(mon, x="Month_Name", y="Count", markers=True, title="Monthly activity")
        fig.update_layout(xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 5 — Environmental Conditions
# --------------------------------------------------------------------------
with tab_env:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Temperature vs Observations")
        fig = px.histogram(
            f, x="Temperature", color="Location_Type", nbins=25, barmode="overlay",
            opacity=0.65, color_discrete_map=HABITAT_COLORS,
        )
        fig.update_layout(legend_title="Habitat")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Humidity vs Observations")
        fig = px.histogram(
            f, x="Humidity", color="Location_Type", nbins=25, barmode="overlay",
            opacity=0.65, color_discrete_map=HABITAT_COLORS,
        )
        fig.update_layout(legend_title="Habitat")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sky Condition Breakdown")
    sky_counts = f.groupby(["Sky", "Location_Type"]).size().reset_index(name="Count")
    fig = px.bar(sky_counts, x="Sky", y="Count", color="Location_Type",
                 color_discrete_map=HABITAT_COLORS, barmode="group")
    fig.update_layout(xaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Disturbance Effect on Observations")
    dist_counts = f["Disturbance"].value_counts().reset_index()
    dist_counts.columns = ["Disturbance", "Count"]
    fig = px.bar(dist_counts, x="Disturbance", y="Count", color="Disturbance")
    fig.update_layout(showlegend=False, xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 6 — Distance & Behavior
# --------------------------------------------------------------------------
with tab_behavior:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Observation Distance")
        dist_counts = f["Distance"].value_counts().reset_index()
        dist_counts.columns = ["Distance", "Count"]
        fig = px.pie(dist_counts, names="Distance", values="Count", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Flyover Frequency")
        fly_counts = f["Flyover_Observed"].value_counts().reset_index()
        fly_counts.columns = ["Flyover_Observed", "Count"]
        fly_counts["Flyover_Observed"] = fly_counts["Flyover_Observed"].map(
            {True: "Flyover", False: "Not a flyover"}
        )
        fig = px.bar(fly_counts, x="Flyover_Observed", y="Count", color="Flyover_Observed")
        fig.update_layout(showlegend=False, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distance by Habitat")
    db = f.groupby(["Distance", "Location_Type"]).size().reset_index(name="Count")
    fig = px.bar(db, x="Distance", y="Count", color="Location_Type",
                 color_discrete_map=HABITAT_COLORS, barmode="group")
    fig.update_layout(xaxis_title="", legend_title="Habitat")
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 7 — Observer Trends
# --------------------------------------------------------------------------
with tab_observer:
    st.subheader("Observations Logged per Observer")
    obs_counts = f["Observer"].value_counts().reset_index()
    obs_counts.columns = ["Observer", "Observations"]
    fig = px.bar(obs_counts, x="Observer", y="Observations", color="Observer")
    fig.update_layout(showlegend=False, xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Species Diversity Reported per Observer")
        obs_div = f.groupby("Observer")["Scientific_Name"].nunique().reset_index(name="Unique Species")
        obs_div = obs_div.sort_values("Unique Species", ascending=False)
        fig = px.bar(obs_div, x="Observer", y="Unique Species", color="Observer")
        fig.update_layout(showlegend=False, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Effect of Repeat Visits")
        visit_counts = f.groupby("Visit")["Scientific_Name"].nunique().reset_index(name="Unique Species")
        fig = px.line(visit_counts, x="Visit", y="Unique Species", markers=True)
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# TAB 8 — Conservation Insights
# --------------------------------------------------------------------------
with tab_conservation:
    watch_df = f[f["PIF_Watchlist_Status"] == True]  # noqa: E712
    stew_df = f[f["Regional_Stewardship_Status"] == True]  # noqa: E712

    c1, c2 = st.columns(2)
    c1.metric("Watchlist Observations", f"{len(watch_df):,}")
    c2.metric("Regional Stewardship Observations", f"{len(stew_df):,}")

    st.subheader("PIF Watchlist Species — Observation Counts")
    if not watch_df.empty:
        wc = watch_df["Common_Name"].value_counts().reset_index()
        wc.columns = ["Common_Name", "Count"]
        fig = px.bar(wc, x="Common_Name", y="Count", color="Count",
                     color_continuous_scale="OrRd")
        fig.update_layout(xaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No watchlist species observations under the current filters.")

    st.subheader("Watchlist Species by Habitat")
    if not watch_df.empty:
        wh = watch_df.groupby(["Location_Type"]).size().reset_index(name="Count")
        fig = px.pie(wh, names="Location_Type", values="Count", hole=0.45,
                     color="Location_Type", color_discrete_map=HABITAT_COLORS)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Regional Stewardship Species — Observation Counts")
    if not stew_df.empty:
        sc = stew_df["Common_Name"].value_counts().reset_index()
        sc.columns = ["Common_Name", "Count"]
        fig = px.bar(sc, x="Common_Name", y="Count", color="Count",
                     color_continuous_scale="Blues")
        fig.update_layout(xaxis_title="", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No regional stewardship species observations under the current filters.")

# --------------------------------------------------------------------------
# TAB 9 — Raw Data Explorer
# --------------------------------------------------------------------------
with tab_raw:
    st.subheader("Filtered Data Explorer")
    st.caption(f"Showing {len(f):,} of {len(df):,} total cleaned observations.")
    st.dataframe(f, use_container_width=True, height=500)
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=f.to_csv(index=False).encode("utf-8"),
        file_name="bird_observations_filtered.csv",
        mime="text/csv",
    )

st.markdown("---")
st.caption(
    "Data: NPS bird monitoring program (Forest & Grassland plots) · "
    "Built with Streamlit + Plotly + PostgreSQL"
)

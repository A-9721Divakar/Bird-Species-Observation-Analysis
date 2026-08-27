# 🐦 Bird Species Observation Analysis

An interactive Streamlit dashboard analyzing bird species distribution and
diversity across **Forest** and **Grassland** habitats, built from National
Park Service bird monitoring data. Covers data cleaning, PostgreSQL storage,
and a multi-tab, filterable dashboard with Plotly visualizations.

## What's in this project

```
bird-species-dashboard/
├── app.py                     # Streamlit dashboard (run this)
├── clean_data.py              # Cleans raw CSVs, loads into PostgreSQL
├── db_utils.py                # Data-loading helper (PostgreSQL + CSV fallback)
├── requirements.txt
├── .env.example                # Copy to .env and fill in your DB credentials
├── .gitignore
├── .streamlit/config.toml      # Theme
└── data/
    ├── raw/                    # Original FOREST & GRASSLAND CSVs
    └── cleaned/                # Cleaned, combined dataset (generated)
```

## 1. Setup

```bash
# clone/open the project folder, then:
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. (Optional but recommended) Set up PostgreSQL

The project follows the "store data in SQL for visualization" requirement.

1. Install PostgreSQL locally (or use any hosted Postgres — Supabase,
   Render, Railway, ElephantSQL, etc.).
2. Create a database, e.g. `bird_observations_db`.
3. Copy `.env.example` to `.env` and fill in your credentials:

   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=bird_observations_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

> **No PostgreSQL yet?** That's fine — skip this step. `clean_data.py` and
> `app.py` both automatically fall back to a local cleaned CSV file, so the
> dashboard runs and looks identical either way. Add PostgreSQL later
> whenever you're ready; nothing else needs to change.

## 3. Clean the data (run once)

```bash
python clean_data.py
```

This will:
- Load the raw Forest & Grassland CSVs from `data/raw/`
- Standardize the two schemas and combine them into one dataset
- Handle missing values, fix data types, and engineer helper columns
  (`Month`, `Season`, `Time_Of_Day`, `Observation_Duration_Min`)
- Save the result to `data/cleaned/bird_data_cleaned.csv`
- Push it to PostgreSQL (`bird_observations` table) if `.env` is configured

## 4. Run the dashboard

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## Dashboard tabs

| Tab | What it shows |
|---|---|
| 📊 Overview | KPIs, habitat split, species richness, top species |
| 📅 Temporal | Monthly/seasonal trends, time-of-day activity, year×month heatmap |
| 🗺️ Spatial | Observations by site/plot, biodiversity hotspots |
| 🦉 Species | Sex ratio, ID method, per-species deep dive |
| 🌦️ Environment | Temperature/humidity distributions, sky, disturbance effects |
| 📏 Distance & Behavior | Observation distance, flyover frequency |
| 🧑‍🔬 Observers | Observations & diversity per observer, repeat-visit effect |
| 🛡️ Conservation | PIF Watchlist & Regional Stewardship species insights |
| 📄 Raw Data | Filtered table + CSV download |

All charts respond to the sidebar filters (habitat, year, species, sex,
observer, watchlist-only, flyovers-only, date range).

## Deploying (GitHub + Streamlit Community Cloud)

1. **Push to GitHub**

   ```bash
   git init
   git add .
   git commit -m "Bird Species Observation Analysis dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/bird-species-dashboard.git
   git push -u origin main
   ```

   `.env` is already excluded via `.gitignore` — never commit real DB
   credentials.

2. **Deploy on Streamlit Community Cloud** (free)
   - Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
     GitHub.
   - Click **New app**, pick this repo and branch, set the main file to
     `app.py`.
   - Under **Advanced settings → Secrets**, add your PostgreSQL credentials
     in the same shape as `.env`:
     ```
     DB_HOST = "..."
     DB_PORT = "5432"
     DB_NAME = "..."
     DB_USER = "..."
     DB_PASSWORD = "..."
     ```
     (Or skip this — the app will use the bundled cleaned CSV instead.)
   - Click **Deploy**. You'll get a public `*.streamlit.app` URL to share
     with your mentor.

## Notes on the data

- Source files (`data/raw/`) cover a single administrative unit (ANTI —
  Antietam National Battlefield) for 2018, with 333 Forest observations and
  3,130 Grassland observations.
- The Forest and Grassland exports don't share an identical schema (e.g.
  `Site_Name`/`NPSTaxonCode` vs `TaxonCode`/`Previously_Obs`) —
  `clean_data.py` unifies these into one combined table.
- No GPS coordinates are provided, so "spatial analysis" compares sites and
  plots by observation volume/species richness rather than a geographic map.

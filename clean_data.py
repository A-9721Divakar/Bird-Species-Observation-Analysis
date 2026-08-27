"""
clean_data.py
--------------
Bird Species Observation Analysis — Data Cleaning & Preprocessing

What this script does:
1. Loads the raw FOREST and GRASSLAND monitoring CSVs.
2. Standardizes both schemas so they can be safely combined (the two source
   files don't have identical columns - e.g. FOREST has Site_Name +
   NPSTaxonCode, GRASSLAND has TaxonCode + Previously_Obs).
3. Cleans missing values, fixes data types, and engineers a few analysis-
   friendly columns (Month, Season, Time_Of_Day, Observation_Duration_Min).
4. Saves the cleaned, combined dataset to:
      - data/cleaned/bird_data_cleaned.csv   (always — used as an offline
        fallback by the dashboard so it keeps working even without a DB)
      - a PostgreSQL table (bird_observations) if DB credentials are found
        in a .env file — used as the primary source by the dashboard.

Run this once before launching the Streamlit app:
    python clean_data.py
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
RAW_FOREST = BASE_DIR / "data" / "raw" / "Bird_Monitoring_Data_FOREST.csv"
RAW_GRASSLAND = BASE_DIR / "data" / "raw" / "Bird_Monitoring_Data_GRASSLAND.csv"
CLEANED_DIR = BASE_DIR / "data" / "cleaned"
CLEANED_CSV = CLEANED_DIR / "bird_data_cleaned.csv"

CLEANED_DIR.mkdir(parents=True, exist_ok=True)


def load_raw(path: Path, habitat_label: str) -> pd.DataFrame:
    """Load one raw CSV and tag it with its habitat (for a sanity check)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path}. Make sure the raw CSV files are in data/raw/."
        )
    df = pd.read_csv(path)
    df["Location_Type"] = df["Location_Type"].fillna(habitat_label)
    return df


def unify_schema(forest: pd.DataFrame, grassland: pd.DataFrame) -> pd.DataFrame:
    """
    Align the two datasets onto one common schema.

    FOREST-only columns : Site_Name, NPSTaxonCode
    GRASSLAND-only columns: TaxonCode, Previously_Obs

    We keep the union of all columns. Where a dataset is missing a column,
    it is filled with NaN so the combined frame stays rectangular.
    """
    all_columns = sorted(set(forest.columns) | set(grassland.columns))

    for col in all_columns:
        if col not in forest.columns:
            forest[col] = np.nan
        if col not in grassland.columns:
            grassland[col] = np.nan

    # A single unified taxon-code column is more useful downstream than two
    # habitat-specific ones.
    combined = pd.concat([forest[all_columns], grassland[all_columns]], ignore_index=True)
    combined["Taxon_Code"] = combined["NPSTaxonCode"].combine_first(combined["TaxonCode"])
    combined.drop(columns=["NPSTaxonCode", "TaxonCode"], inplace=True)

    return combined


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, fix types, and engineer helper columns."""
    df = df.copy()

    # ---- Text / categorical cleanup ---------------------------------
    text_cols = [
        "Admin_Unit_Code", "Site_Name", "Plot_Name", "Location_Type",
        "Observer", "Interval_Length", "ID_Method", "Distance", "Sex",
        "Common_Name", "Scientific_Name", "AOU_Code", "Sky", "Wind",
        "Disturbance",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Sex: unify blanks/NaN as "Undetermined" (matches the value already used
    # in the source data), and normalize the odd "0" placeholder in Distance.
    df["Sex"] = df["Sex"].fillna("Undetermined")
    df["Distance"] = df["Distance"].replace({"0": np.nan})
    df["Distance"] = df["Distance"].fillna("Not Recorded")

    # Site_Name isn't present for grassland plots — derive a readable one
    # from the admin unit so every row still has a usable site label.
    df["Site_Name"] = df["Site_Name"].fillna(df["Admin_Unit_Code"] + " (Grassland Unit)")

    # ---- Boolean columns ----------------------------------------------
    bool_cols = [
        "Flyover_Observed", "PIF_Watchlist_Status", "Regional_Stewardship_Status",
        "Initial_Three_Min_Cnt", "Previously_Obs",
    ]
    for col in bool_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.upper()
                .map({"TRUE": True, "FALSE": False})
            )
            if col == "Previously_Obs":
                df[col] = df[col].fillna(False)  # not tracked for FOREST rows

    # ---- Numeric columns ------------------------------------------------
    numeric_cols = ["Temperature", "Humidity", "AcceptedTSN", "Taxon_Code", "Visit", "Year"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with no species identified at all — not usable for analysis.
    df = df.dropna(subset=["Common_Name", "Scientific_Name"])

    # ---- Dates & times ----------------------------------------------------
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.month_name()

    season_map = {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Fall", 10: "Fall", 11: "Fall",
    }
    df["Season"] = df["Month"].map(season_map)

    # Start/End time are stored as full timestamps with a bogus 1899 date
    # (an Excel export artifact) — we only care about the time-of-day part.
    for col in ["Start_Time", "End_Time"]:
        parsed = pd.to_datetime(df[col], errors="coerce")
        df[col] = parsed.dt.strftime("%H:%M:%S")
        df[f"{col}_dt"] = parsed

    df["Observation_Duration_Min"] = (
        (df["End_Time_dt"] - df["Start_Time_dt"]).dt.total_seconds() / 60
    ).round(1)
    df.loc[df["Observation_Duration_Min"] < 0, "Observation_Duration_Min"] = np.nan

    def time_bucket(dt):
        if pd.isna(dt):
            return "Unknown"
        h = dt.hour
        if h < 8:
            return "Early Morning (before 8am)"
        elif h < 10:
            return "Morning (8-10am)"
        elif h < 12:
            return "Late Morning (10am-12pm)"
        else:
            return "Afternoon (after 12pm)"

    df["Time_Of_Day"] = df["Start_Time_dt"].apply(time_bucket)
    df.drop(columns=["Start_Time_dt", "End_Time_dt"], inplace=True)

    # ---- Final tidy up ------------------------------------------------
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    df.insert(0, "Observation_ID", df.index + 1)

    return df


def save_to_postgres(df: pd.DataFrame) -> bool:
    """Push the cleaned dataframe to PostgreSQL if credentials are configured."""
    load_dotenv(BASE_DIR / ".env")

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([db_host, db_name, db_user, db_password]):
        print(
            "\n[INFO] No PostgreSQL credentials found in .env — skipping database "
            "load. The dashboard will read the cleaned CSV instead.\n"
            "        Copy .env.example to .env and fill in your DB details to "
            "enable PostgreSQL.\n"
        )
        return False

    try:
        from sqlalchemy import create_engine

        engine = create_engine(
            f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        df.to_sql("bird_observations", engine, if_exists="replace", index=False)
        print(f"[OK] Loaded {len(df):,} rows into PostgreSQL table 'bird_observations'.")
        return True
    except Exception as exc:  # noqa: BLE001 — surfaced to the user, not swallowed
        print(f"[WARN] Could not write to PostgreSQL ({exc}).")
        print("       The dashboard will fall back to the cleaned CSV file.")
        return False


def main():
    print("Loading raw data...")
    forest = load_raw(RAW_FOREST, "Forest")
    grassland = load_raw(RAW_GRASSLAND, "Grassland")
    print(f"  Forest rows:    {len(forest):,}")
    print(f"  Grassland rows: {len(grassland):,}")

    print("Unifying schema...")
    combined = unify_schema(forest, grassland)

    print("Cleaning & engineering features...")
    cleaned = clean_dataset(combined)
    print(f"  Cleaned rows:   {len(cleaned):,}")
    print(f"  Columns:        {list(cleaned.columns)}")

    cleaned.to_csv(CLEANED_CSV, index=False)
    print(f"[OK] Saved cleaned dataset to {CLEANED_CSV}")

    save_to_postgres(cleaned)
    print("\nDone. You can now run:  streamlit run app.py")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"\n[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

"""
db_utils.py
------------
Single place that knows how to fetch the cleaned bird observation data.

Tries PostgreSQL first (using credentials from .env). If that fails for any
reason — no .env, DB not running, wrong credentials — it transparently falls
back to the cleaned CSV so the dashboard always has data to show.
"""

from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent
CLEANED_CSV = BASE_DIR / "data" / "cleaned" / "bird_data_cleaned.csv"

load_dotenv(BASE_DIR / ".env")


def _get_engine():
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([db_host, db_name, db_user, db_password]):
        return None

    from sqlalchemy import create_engine

    return create_engine(
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


@st.cache_data(ttl=600, show_spinner="Loading bird observation data...")
def load_data() -> tuple[pd.DataFrame, str]:
    """
    Returns (dataframe, source_label).
    source_label is either "PostgreSQL" or "Local CSV (fallback)" so the UI
    can be transparent about where the data came from.
    """
    engine = _get_engine()
    if engine is not None:
        try:
            df = pd.read_sql("SELECT * FROM bird_observations", engine)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            return df, "PostgreSQL"
        except Exception:
            pass  # fall through to CSV

    if not CLEANED_CSV.exists():
        raise FileNotFoundError(
            "No data available. Run `python clean_data.py` first to generate "
            "the cleaned dataset."
        )

    df = pd.read_csv(CLEANED_CSV)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df, "Local CSV (fallback)"

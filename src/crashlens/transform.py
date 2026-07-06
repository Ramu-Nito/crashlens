"""Transforms: clean the raw API frame and load it into the DuckDB warehouse."""

from __future__ import annotations

import logging

import duckdb
import numpy as np
import pandas as pd

from crashlens import config

logger = logging.getLogger(__name__)

INJURY_COLS = {
    "number_of_persons_injured": "persons_injured",
    "number_of_persons_killed": "persons_killed",
    "number_of_pedestrians_injured": "pedestrians_injured",
    "number_of_pedestrians_killed": "pedestrians_killed",
    "number_of_cyclist_injured": "cyclists_injured",
    "number_of_cyclist_killed": "cyclists_killed",
    "number_of_motorist_injured": "motorists_injured",
    "number_of_motorist_killed": "motorists_killed",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw Socrata rows into a typed, analysis-ready frame."""
    out = df.copy()

    out["collision_id"] = pd.to_numeric(out["collision_id"], errors="coerce")
    out = out.dropna(subset=["collision_id"]).astype({"collision_id": "int64"})
    out = out.drop_duplicates(subset="collision_id")

    # Combine date + time into one timestamp; drop unparseable rows.
    date_part = pd.to_datetime(out["crash_date"], errors="coerce").dt.date.astype(str)
    out["crash_datetime"] = pd.to_datetime(
        date_part + " " + out["crash_time"].fillna("00:00"), errors="coerce"
    )
    out = out.dropna(subset=["crash_datetime"])

    out["borough"] = out["borough"].fillna("UNKNOWN").str.upper().str.strip()

    # Coordinates: numeric, and null out obviously-bad geocodes (0,0 or outside NYC).
    for col, (lo, hi) in [("latitude", (40.4, 41.0)), ("longitude", (-74.3, -73.6))]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out.loc[~out[col].between(lo, hi), col] = np.nan

    for raw, new in INJURY_COLS.items():
        out[new] = pd.to_numeric(out.get(raw), errors="coerce").fillna(0).astype("int64")

    out["contributing_factor"] = (
        out["contributing_factor_vehicle_1"].fillna("Unspecified").str.strip()
    )
    out["vehicle_type"] = (
        out["vehicle_type_code1"].fillna("Unknown").str.strip().str.title()
    )

    # Derived columns for analysis.
    out["crash_year"] = out["crash_datetime"].dt.year
    out["crash_month"] = out["crash_datetime"].dt.to_period("M").astype(str)
    out["crash_hour"] = out["crash_datetime"].dt.hour
    out["day_of_week"] = out["crash_datetime"].dt.day_name()
    out["is_fatal"] = out["persons_killed"] > 0

    keep = [
        "collision_id", "crash_datetime", "crash_year", "crash_month", "crash_hour",
        "day_of_week", "borough", "latitude", "longitude", "persons_injured",
        "persons_killed", "pedestrians_injured", "pedestrians_killed",
        "cyclists_injured", "cyclists_killed", "motorists_injured",
        "motorists_killed", "contributing_factor", "vehicle_type", "is_fatal",
    ]
    return out[keep].reset_index(drop=True)


def load_warehouse(df: pd.DataFrame) -> None:
    """Write the cleaned frame into DuckDB as the `crashes` table."""
    config.WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DUCKDB_PATH))
    try:
        con.execute("CREATE OR REPLACE TABLE crashes AS SELECT * FROM df")
        n = con.execute("SELECT COUNT(*) FROM crashes").fetchone()[0]
        logger.info("Loaded %s rows into %s", n, config.DUCKDB_PATH)
    finally:
        con.close()

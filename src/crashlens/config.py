"""Central configuration for paths and API endpoints."""

from pathlib import Path

# Project root = two levels up from this file (src/crashlens/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"

RAW_PARQUET = RAW_DIR / "crashes_raw.parquet"
DUCKDB_PATH = WAREHOUSE_DIR / "crashlens.duckdb"

# NYC Open Data — Motor Vehicle Collisions (Crashes), Socrata SODA API.
# No API key required for moderate use; an app token raises the rate limit.
SOCRATA_URL = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"

# Only pull crashes from this date forward (keeps the dataset a manageable size).
MIN_CRASH_DATE = "2023-01-01"

# Columns we request from the API (keeps payloads small).
SOCRATA_COLUMNS = [
    "collision_id",
    "crash_date",
    "crash_time",
    "borough",
    "latitude",
    "longitude",
    "number_of_persons_injured",
    "number_of_persons_killed",
    "number_of_pedestrians_injured",
    "number_of_pedestrians_killed",
    "number_of_cyclist_injured",
    "number_of_cyclist_killed",
    "number_of_motorist_injured",
    "number_of_motorist_killed",
    "contributing_factor_vehicle_1",
    "vehicle_type_code1",
]

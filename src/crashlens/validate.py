"""Data validation with pandera.

The raw API data is messy: missing boroughs, zeroed-out coordinates, string
numbers. This schema checks the *cleaned* frame so downstream consumers
(warehouse, dashboard) can trust it.
"""

from __future__ import annotations

import logging

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column

logger = logging.getLogger(__name__)

# NYC bounding box — anything outside is a bad geocode.
NYC_LAT = (40.4, 41.0)
NYC_LON = (-74.3, -73.6)

VALID_BOROUGHS = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND", "UNKNOWN"]

clean_schema = pa.DataFrameSchema(
    {
        "collision_id": Column(int, unique=True),
        "crash_datetime": Column("datetime64[ns]"),
        "borough": Column(str, Check.isin(VALID_BOROUGHS)),
        "latitude": Column(float, Check.in_range(*NYC_LAT), nullable=True),
        "longitude": Column(float, Check.in_range(*NYC_LON), nullable=True),
        "persons_injured": Column(int, Check.ge(0)),
        "persons_killed": Column(int, Check.ge(0)),
        "pedestrians_injured": Column(int, Check.ge(0)),
        "cyclists_injured": Column(int, Check.ge(0)),
        "motorists_injured": Column(int, Check.ge(0)),
        "contributing_factor": Column(str),
        "vehicle_type": Column(str),
    },
    strict=False,  # allow extra derived columns
    coerce=True,
)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the cleaned frame; raises pandera.errors.SchemaErrors on failure."""
    validated = clean_schema.validate(df, lazy=True)
    logger.info("Validation passed for %s rows", len(validated))
    return validated

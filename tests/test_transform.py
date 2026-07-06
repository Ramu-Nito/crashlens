import pandas as pd
import pytest

from crashlens import transform


@pytest.fixture
def raw_sample() -> pd.DataFrame:
    """A raw frame mimicking messy Socrata output."""
    return pd.DataFrame(
        {
            "collision_id": ["1001", "1002", "1002", "bad", "1004"],
            "crash_date": [
                "2024-03-01T00:00:00.000",
                "2024-03-02T00:00:00.000",
                "2024-03-02T00:00:00.000",
                "2024-03-03T00:00:00.000",
                "not-a-date",
            ],
            "crash_time": ["14:30", "8:05", "8:05", "12:00", "9:00"],
            "borough": ["brooklyn", None, None, "QUEENS", "BRONX"],
            "latitude": ["40.71", "0.0", "0.0", "40.85", "40.60"],
            "longitude": ["-73.95", "0.0", "0.0", "-73.90", "-74.00"],
            "number_of_persons_injured": ["2", None, None, "1", "0"],
            "number_of_persons_killed": ["0", "0", "0", "1", "0"],
            "number_of_pedestrians_injured": ["1", "0", "0", "0", "0"],
            "number_of_pedestrians_killed": ["0", "0", "0", "0", "0"],
            "number_of_cyclist_injured": ["0", "0", "0", "0", "0"],
            "number_of_cyclist_killed": ["0", "0", "0", "0", "0"],
            "number_of_motorist_injured": ["1", "0", "0", "1", "0"],
            "number_of_motorist_killed": ["0", "0", "0", "1", "0"],
            "contributing_factor_vehicle_1": ["Driver Inattention/Distraction", None, None, "Unsafe Speed", "Unspecified"],
            "vehicle_type_code1": ["SEDAN", "taxi", "taxi", None, "Bike"],
        }
    )


def test_clean_drops_bad_ids_dates_and_dupes(raw_sample):
    out = transform.clean(raw_sample)
    # 1002 deduped, "bad" id dropped, "not-a-date" dropped -> 2 rows remain
    assert set(out["collision_id"]) == {1001, 1002}


def test_clean_normalizes_borough(raw_sample):
    out = transform.clean(raw_sample)
    row = out[out["collision_id"] == 1001].iloc[0]
    assert row["borough"] == "BROOKLYN"
    assert out[out["collision_id"] == 1002].iloc[0]["borough"] == "UNKNOWN"


def test_clean_nulls_bad_coordinates(raw_sample):
    out = transform.clean(raw_sample)
    row = out[out["collision_id"] == 1002].iloc[0]
    assert pd.isna(row["latitude"]) and pd.isna(row["longitude"])


def test_clean_types_and_derived_columns(raw_sample):
    out = transform.clean(raw_sample)
    row = out[out["collision_id"] == 1001].iloc[0]
    assert row["persons_injured"] == 2
    assert row["crash_year"] == 2024
    assert row["crash_hour"] == 14
    assert row["day_of_week"] == "Friday"
    assert bool(row["is_fatal"]) is False

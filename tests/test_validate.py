import pandas as pd
import pandera.pandas as pa
import pytest

from crashlens import transform, validate


def _clean_frame(**overrides) -> pd.DataFrame:
    base = {
        "collision_id": [1],
        "crash_datetime": [pd.Timestamp("2024-06-01 10:00")],
        "borough": ["QUEENS"],
        "latitude": [40.7],
        "longitude": [-73.9],
        "persons_injured": [0],
        "persons_killed": [0],
        "pedestrians_injured": [0],
        "cyclists_injured": [0],
        "motorists_injured": [0],
        "contributing_factor": ["Unspecified"],
        "vehicle_type": ["Sedan"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_valid_frame_passes():
    assert len(validate.validate(_clean_frame())) == 1


def test_bad_borough_fails():
    with pytest.raises(pa.errors.SchemaErrors):
        validate.validate(_clean_frame(borough=["ATLANTIS"]))


def test_negative_injuries_fail():
    with pytest.raises(pa.errors.SchemaErrors):
        validate.validate(_clean_frame(persons_injured=[-1]))


def test_out_of_nyc_coordinates_fail():
    with pytest.raises(pa.errors.SchemaErrors):
        validate.validate(_clean_frame(latitude=[34.05]))  # Los Angeles


def test_clean_output_conforms_to_schema():
    raw = pd.DataFrame(
        {
            "collision_id": ["5001"],
            "crash_date": ["2024-05-10T00:00:00.000"],
            "crash_time": ["17:45"],
            "borough": ["manhattan"],
            "latitude": ["40.75"],
            "longitude": ["-73.98"],
            "number_of_persons_injured": ["1"],
            "number_of_persons_killed": ["0"],
            "number_of_pedestrians_injured": ["0"],
            "number_of_pedestrians_killed": ["0"],
            "number_of_cyclist_injured": ["1"],
            "number_of_cyclist_killed": ["0"],
            "number_of_motorist_injured": ["0"],
            "number_of_motorist_killed": ["0"],
            "contributing_factor_vehicle_1": ["Failure to Yield Right-of-Way"],
            "vehicle_type_code1": ["SEDAN"],
        }
    )
    assert len(validate.validate(transform.clean(raw))) == 1

"""Unit tests for the citizen data-quality validator.

These lock in the behaviour that the AI-Supported Assessment story depends on:
junk names, swapped coordinates, duplicates, and out-of-region detection.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import quality  # noqa: E402


def _one(name="River X", lat=40.2, lon=-8.42):
    return pd.DataFrame([{"name": name, "latitude": lat, "longitude": lon}])


def test_valid_partner_site_is_ok():
    res = quality.validate_submissions(_one("Ribeira do Mondego", 40.2, -8.42))
    assert res.df.iloc[0]["status"] == "OK"


@pytest.mark.parametrize("name", ["test", "Test", "test123", "Random", "fgdgh", "This site", ""])
def test_junk_names_flagged(name):
    res = quality.validate_submissions(_one(name, 40.2, -8.42))
    assert "JUNK_NAME" in res.df.iloc[0]["flags"]


def test_swapped_coordinates_detected_and_suggested():
    # Ghent is ~51.05N, 3.72E. A swapped entry lands at lat 3.72, lon 51.05.
    res = quality.validate_submissions(_one("Zwalm", 3.72, 51.05))
    row = res.df.iloc[0]
    assert "LIKELY_SWAPPED" in row["flags"]
    assert row["suggestion"]["swapped_latlon"] == (51.05, 3.72)


def test_invalid_coords_flagged():
    res = quality.validate_submissions(_one("Bad", 200.0, 999.0))
    assert "INVALID_COORDS" in res.df.iloc[0]["flags"]


def test_duplicates_within_radius():
    df = pd.DataFrame([
        {"name": "Site 3", "latitude": 50.813471, "longitude": 3.779874},
        {"name": "Site 3", "latitude": 50.813441, "longitude": 3.779926},  # ~5 m away
    ])
    res = quality.validate_submissions(df)
    assert all("DUPLICATE" in f for f in res.df["flags"])


def test_far_apart_not_duplicate():
    df = pd.DataFrame([
        {"name": "A", "latitude": 40.2, "longitude": -8.42},
        {"name": "B", "latitude": 41.1, "longitude": 14.78},
    ])
    res = quality.validate_submissions(df)
    assert not any("DUPLICATE" in f for f in res.df["flags"])


def test_out_of_region_flagged():
    # San Jose, USA — valid coordinates but not in a partner country.
    res = quality.validate_submissions(_one("San Jose", 37.3354, -121.893))
    assert "OUT_OF_REGION" in res.df.iloc[0]["flags"]


def test_real_dataset_summary_shape():
    from aquasentinel import data
    res = quality.validate_submissions(data.load_user_generated())
    s = res.summary
    assert s["n_total"] == 71
    assert s["n_review"] + s["n_ok"] == s["n_total"]
    assert s["junk_name"] >= 5 and s["duplicate"] >= 5

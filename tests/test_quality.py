"""Unit tests for the citizen data-quality validator.

These lock in the behaviour the AI-Supported Assessment story depends on: junk
names, swapped coordinates, duplicate clusters, and — importantly — that a valid
site outside the partner cities is NOT treated as an error.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, quality  # noqa: E402


def _one(name="River X", lat=40.2, lon=-8.42):
    return pd.DataFrame([{"name": name, "latitude": lat, "longitude": lon}])


def _real():
    return quality.validate_submissions(data.load_user_generated(),
                                        reference=data.research_points())


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


def test_swap_detected_outside_partner_countries():
    """A swap far from Europe is caught when the corrected point sits next to
    known points (here: two neighbouring registrations in Curitiba, Brazil)."""
    df = pd.DataFrame([
        {"name": "Riacho A", "latitude": -25.443198, "longitude": -49.354184},
        {"name": "Ribeirao C", "latitude": -25.436872, "longitude": -49.359575},
        {"name": "Rio B", "latitude": -49.274376, "longitude": -25.414426},   # swapped
    ])
    res = quality.validate_submissions(df)
    assert list(res.df["flags"][:2]) == ["OK", "OK"]
    assert "LIKELY_SWAPPED" in res.df.iloc[2]["flags"]
    assert res.df.iloc[2]["suggestion"]["swapped_latlon"] == (-25.414426, -49.274376)


def test_ambiguous_pair_is_not_guessed():
    """Two lone points that are each other's swap: nothing tells us which is wrong,
    so neither is flagged."""
    df = pd.DataFrame([
        {"name": "Riacho A", "latitude": -25.443198, "longitude": -49.354184},
        {"name": "Rio B", "latitude": -49.274376, "longitude": -25.414426},
    ])
    res = quality.validate_submissions(df)
    assert not any("LIKELY_SWAPPED" in f for f in res.df["flags"])


def test_invalid_coords_flagged():
    res = quality.validate_submissions(_one("Bad", 200.0, 999.0))
    assert "INVALID_COORDS" in res.df.iloc[0]["flags"]


def test_duplicates_within_radius_form_one_cluster():
    df = pd.DataFrame([
        {"name": "Site 3", "latitude": 50.813471, "longitude": 3.779874},
        {"name": "Site 3", "latitude": 50.813441, "longitude": 3.779926},  # ~5 m away
    ])
    res = quality.validate_submissions(df)
    assert all("DUPLICATE" in f for f in res.df["flags"])
    assert res.summary["duplicate"] == 2 and res.summary["duplicate_clusters"] == 1
    assert res.df["cluster"].nunique() == 1


def test_far_apart_not_duplicate():
    df = pd.DataFrame([
        {"name": "A", "latitude": 40.2, "longitude": -8.42},
        {"name": "B", "latitude": 41.1, "longitude": 14.78},
    ])
    res = quality.validate_submissions(df)
    assert not any("DUPLICATE" in f for f in res.df["flags"])


def test_site_outside_coverage_is_a_note_not_an_error():
    # San Jose, USA — a perfectly valid citizen site, just far from lab coverage.
    res = quality.validate_submissions(_one("San Jose creek", 37.3354, -121.893),
                                       reference=data.research_points())
    row = res.df.iloc[0]
    assert row["status"] == "OK" and row["flags"] == "OK"
    assert "OUTSIDE_COVERAGE" in row["notes"]


def test_real_dataset_summary():
    s = _real().summary
    assert s["n_total"] == 71
    assert s["n_review"] + s["n_ok"] == s["n_total"]
    assert s["junk_name"] >= 5 and s["duplicate"] >= 5
    assert s["likely_swapped"] == 3          # Zwalm + two Rio Pilarzinho entries
    assert s["duplicate_clusters"] < s["duplicate"]


def test_cleaned_registry_applies_the_fixes():
    res = _real()
    clean = quality.cleaned_registry(res)
    assert len(clean) < res.summary["n_total"]
    assert not clean["name"].str.lower().str.contains("test").any()
    # every registration is either dropped as junk or accounted for in a merged site
    assert clean["registrations_merged"].sum() == res.summary["n_total"] - res.summary["junk_name"]
    # swapped rows were moved to the corrected position
    zwalm = clean[clean["name"] == "Zwalm"].iloc[0]
    assert zwalm["latitude"] > 50 and zwalm["longitude"] < 4


def test_assess_new_submission_at_entry_time():
    ug, ref = data.load_user_generated(), data.research_points()
    swapped = quality.assess_new_submission("Zwalm", 3.71, 50.88, ug, ref)
    assert "LIKELY_SWAPPED" in swapped["flags"]
    assert swapped["nearest_monitored_km"] < 5       # judged on the corrected position

    dup = quality.assess_new_submission("My stream", 50.81345, 3.77993, ug, ref)
    assert dup["duplicate_of"] and dup["duplicate_of"]["distance_m"] <= quality.DUP_RADIUS_M

    # an existing swapped registration must not vouch for a new swapped one
    brazil = quality.assess_new_submission("Rio X", -49.27, -25.41, ug, ref)
    assert "LIKELY_SWAPPED" in brazil["flags"]

    new = quality.assess_new_submission("Vrishabhavathi", 12.97, 77.59, ug, ref)
    assert new["flags"] == [] and new["outside_coverage"] is True

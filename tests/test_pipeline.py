"""Tests for the data join and feature/model plumbing."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, RISK_COMPONENTS, COMPOSITE  # noqa: E402


def test_analysis_table_one_row_per_site():
    df = data.build_analysis_table()
    assert df["siteCode"].is_unique
    assert len(df) == 106


def test_composite_is_mean_of_components():
    df = data.load_health_risks()
    recomputed = df[RISK_COMPONENTS].mean(axis=1)
    assert np.allclose(recomputed, df[COMPOSITE], atol=1e-3)


def test_coverage_table_counts():
    cov = data.coverage_table()
    assert cov["health_risks"].sum() == 96
    assert cov["sites"].sum() == 106


def test_feature_matrix_has_log_distances():
    df = data.build_analysis_table()
    feat_df, names = features.build_feature_matrix(df)
    assert any(n.startswith("log_distance") for n in names)
    assert "siteCode" in feat_df.columns


def test_plain_labels_exist():
    assert "impervious" in features.plain("imperviousPct1000m")
    assert features.plain("nitrate_mgL") == "nitrate concentration"

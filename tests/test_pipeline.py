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


def test_model_reports_within_city_rank_agreement_and_fair_baseline():
    """Validation must score ranks inside each held-out city (pooling across cities
    overstates skill) and compare against a baseline that never sees that city."""
    import numpy as np
    from aquasentinel import model

    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 3))
    y = X[:, 0] * 0.5 + rng.normal(scale=0.1, size=40)
    cities = np.repeat(["a", "b", "c", "d"], 10)
    m, b, pred, base = model.leave_one_city_out(X, y, cities)
    assert set(m["per_city_spearman"]) == {"a", "b", "c", "d"}
    assert m["mean_city_spearman"] > 0.5
    for c in "abcd":                       # baseline for a city = mean of the OTHER cities
        assert np.isclose(base[cities == c][0], y[cities != c].mean())


def test_conformal_interval_is_calibrated_on_held_out_sites():
    from aquasentinel import model
    df = data.build_analysis_table()
    feat_df, names = features.build_feature_matrix(df)
    tm = model.fit_full(feat_df, df[["siteCode"] + RISK_COMPONENTS], names)
    assert set(tm.conformal_q) == set(RISK_COMPONENTS) | {"composite"}
    assert all(0 < q < 1 for q in tm.conformal_q.values())
    x = feat_df[feat_df["siteCode"] == "C5"][names].to_numpy(float)[0]
    p = model.predict_site(tm, x)["composite"]
    assert p["low"] <= p["pred"] <= p["high"]


def test_interface_text_is_complete_in_both_languages():
    import re
    from aquasentinel.i18n import _STR, LANGS
    for key, entry in _STR.items():
        for lang in LANGS:
            assert entry.get(lang), f"missing {lang} text for {key}"
    app = (Path(__file__).resolve().parents[1] / "app" / "app.py").read_text()
    used = set(re.findall(r"""\bt\(\s*["']([a-z0-9_]+)["']\s*,""", app))
    assert used, "no translation keys found in the app"
    assert not (used - set(_STR)), f"keys used in app but not defined: {sorted(used - set(_STR))}"

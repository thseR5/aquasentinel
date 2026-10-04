"""Tests for the next-campaign planner."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, quality, insights, planning, RISK_COMPONENTS  # noqa: E402


def _ins():
    df = data.build_analysis_table()
    feat_df, names = features.build_feature_matrix(df)
    merged = feat_df.merge(df[["siteCode"] + RISK_COMPONENTS], on="siteCode", how="left")
    q = quality.validate_submissions(data.load_user_generated(), reference=data.research_points())
    ins = insights.discover_all(merged, names, data.load_user_generated(), q.summary)
    return df, [i.to_dict() for i in ins]


def test_sample_size_formulas():
    # Rule out |rho| >= 0.10 needs about 400 sites; a stronger effect needs fewer sites.
    assert 390 <= planning.sites_for_ci(0.10) <= 420
    assert planning.sites_to_detect(0.30, 0.32, 96) < planning.sites_to_detect(0.15, 0.32, 96)
    # An effect exactly at today's bar needs more than today's sites to reach 80% power.
    assert planning.sites_to_detect(0.32, 0.32, 96) > 96
    assert planning.sites_to_detect(0.0, 0.32, 96) is None


def test_rejected_signals_are_closed_and_exploratory_are_reachable():
    _, ins = _ins()
    gaps = {g["id"]: g for g in planning.evidence_gaps(ins)}
    for g in gaps.values():
        if g["verdict"] == "rejected" and g["sites_needed"] is not None:
            assert g["sites_needed"] > planning.NOT_WORTH_IT
        if g["verdict"] == "exploratory":
            assert 96 < g["sites_needed"] <= planning.NOT_WORTH_IT
    assert "INS-ARG-01" in gaps and "INS-CITY-01" in gaps


def test_plan_covers_every_flagged_site_once_with_reasons():
    df, ins = _ins()
    plan = planning.resample_plan(df, ins)
    flagged = {c for i in ins if i["id"] in planning.REASONS for c in i["evidence"]["sites"]}
    assert set(plan["siteCode"]) == flagged and plan["siteCode"].is_unique
    assert (plan["n_reasons"] == plan["reasons"].str.count(";") + 1).all()
    assert plan["n_reasons"].is_monotonic_decreasing
    # The headline sites are on it: every high-ARG site the composite misses.
    arg = next(i for i in ins if i["id"] == "INS-ARG-01")
    assert set(arg["evidence"]["sites"]) <= set(plan["siteCode"])
    assert len(arg["evidence"]["sites"]) == arg["evidence"]["missed_by_composite"]

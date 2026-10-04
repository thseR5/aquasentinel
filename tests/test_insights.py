"""Tests for the Insight Discovery Engine.

The behaviour to protect: the engine must be able to REJECT and to DOWNGRADE its
own findings, every published insight must carry evidence, and the result must be
reproducible run to run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, quality, insights, RISK_COMPONENTS  # noqa: E402


def _merged():
    df = data.build_analysis_table()
    feat_df, names = features.build_feature_matrix(df)
    merged = feat_df.merge(df[["siteCode"] + RISK_COMPONENTS], on="siteCode", how="left")
    return df, merged, names


def _all():
    df, merged, names = _merged()
    q = quality.validate_submissions(data.load_user_generated(), reference=data.research_points())
    return insights.discover_all(merged, names, data.load_user_generated(), q.summary)


def test_every_insight_has_evidence_and_a_verdict():
    ins = _all()
    assert len(ins) >= 8
    for i in ins:
        assert i.evidence and (i.evidence.get("n") or i.evidence.get("n_flagged")), \
            f"{i.id} has no sample-size evidence"
        assert i.limitation and i.next_step
        assert i.challenge["status"] in insights.STATUSES
        assert i.challenge["survives"] == (i.challenge["status"] == "supported")
        assert i.challenge["detail"]


def test_feed_is_ordered_supported_first():
    order = [insights.STATUSES.index(i.challenge["status"]) for i in _all()]
    assert order == sorted(order)


def test_arg_has_no_detectable_faecal_link_but_pathogen_does():
    df, _, _ = _merged()
    (ins,) = insights.arg_independence(df)
    ev = ins.evidence
    assert ins.challenge["status"] == "supported"
    assert ev["ci95"][0] < 0 < ev["ci95"][1]            # faecal-vs-ARG interval spans zero
    assert ev["pathogen_faecal_ci95"][0] > 0.4          # pathogen-vs-faecal clearly positive
    assert 0 < ev["missed_by_composite"] <= ev["top_arg_n"]


def test_fingerprints_are_characterised():
    df, _, _ = _merged()
    lab, profiles, ins = insights.risk_fingerprints(df)
    assert 2 <= len(profiles) <= 6
    assert lab["cluster"].nunique() == len(profiles)
    assert sum(p["n"] for p in profiles.values()) == len(lab)
    for p in profiles.values():
        assert p["n"] > 0 and p["label"] and p["examples"]
    assert 0 < ins.evidence["null_p"] <= 1


def test_challenge_rejects_city_confounded_associations():
    """Some associations must fail the within-city check — proof the challenge
    discriminates rather than rubber-stamping."""
    _, merged, names = _merged()
    status = [a.challenge["status"] for a in insights.associations(merged, names, top=8)]
    assert "rejected" in status
    assert any(s != "rejected" for s in status)


def test_no_association_is_supported_without_clearing_multiple_testing():
    """An association may only be 'supported' if its family-wise p-value clears the
    threshold; anything that merely passes the city check stays 'exploratory'."""
    _, merged, names = _merged()
    for a in insights.associations(merged, names, top=8):
        ch = a.challenge
        if ch["status"] == "supported":
            assert ch["familywise_p"] < insights.ALPHA
        if ch["status"] == "exploratory":
            assert ch["familywise_p"] >= insights.ALPHA


def test_cross_city_reports_component_level_correction():
    df, _, _ = _merged()
    (ins,) = insights.cross_city(df)
    assert set(ins.evidence["component_p"]) == {"pathogen", "faecal", "ARG"}
    assert all(0 <= p <= 1 for p in ins.evidence["component_p"].values())


def test_contradiction_is_arithmetic_and_supported():
    df, _, _ = _merged()
    contra = insights.composite_contradictions(df)
    if contra:
        assert contra[0].challenge["status"] == "supported"


def test_engine_is_reproducible():
    a = [(i.id, i.challenge["status"], i.evidence.get("value")) for i in _all()]
    b = [(i.id, i.challenge["status"], i.evidence.get("value")) for i in _all()]
    assert a == b


def test_wording_does_not_overclaim():
    """Verdicts say 'supported', never 'confirmed', and the ARG headline claims no
    detectable association, not independence."""
    ins = _all()
    assert set(insights.STATUSES) == {"supported", "exploratory", "rejected"}
    arg = next(i for i in ins if i.id == "INS-ARG-01")
    assert "independent" not in arg.title.lower()
    assert "no detectable association" in arg.title.lower()
    for i in ins:
        assert "confirmed" not in (i.title + i.finding).lower()

"""Tests for the Insight Discovery Engine.

The key behaviour to protect: the engine must REJECT its own weak findings — a
city-confounded association has to fail the challenge, and every published insight
must carry evidence (no evidence -> no insight).
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


def test_every_insight_has_evidence():
    df, merged, names = _merged()
    q = quality.validate_submissions(data.load_user_generated())
    ins = insights.discover_all(merged, names, data.load_user_generated(), q.summary)
    assert len(ins) >= 5
    for i in ins:
        assert i.evidence and (i.evidence.get("n") or i.evidence.get("n_flagged")), \
            f"{i.id} has no sample-size evidence"
        assert i.limitation and i.next_step
        assert "survives" in i.challenge


def test_fingerprints_are_characterised():
    df, _, _ = _merged()
    lab, profiles, ins = insights.risk_fingerprints(df)
    assert 2 <= len(profiles) <= 6
    assert lab["cluster"].nunique() == len(profiles)
    for p in profiles.values():
        assert p["n"] > 0 and "dominant" in p and p["examples"]
    # permutation challenge result is present
    assert "survives" in ins.challenge


def test_challenge_can_reject_a_confounded_association():
    """At least one association should be weakened once city structure is removed —
    proving the challenge actually discriminates rather than rubber-stamping."""
    df, merged, names = _merged()
    assoc = insights.associations(merged, names, top=8)
    survived = [a.challenge["survives"] for a in assoc]
    assert any(survived), "no association survived — challenge too harsh"
    assert not all(survived), "no association was rejected — challenge not discriminating"


def test_contradiction_is_arithmetic_and_robust():
    df, _, _ = _merged()
    contra = insights.composite_contradictions(df)
    if contra:  # dataset-dependent, but if present it must be marked robust
        assert contra[0].challenge["survives"] is True

"""Run the Insight Discovery Engine and save results.

Prints each discovered insight with its evidence and challenge outcome, and writes
outputs/insights.json. Run:  python scripts/run_insights.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, quality, insights, planning, RISK_COMPONENTS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"
OUT.mkdir(exist_ok=True)


def main():
    df = data.build_analysis_table()
    df["composite_obs"] = df[RISK_COMPONENTS].mean(axis=1)
    feat_df, names = features.build_feature_matrix(df)
    merged = feat_df.merge(df[["siteCode"] + RISK_COMPONENTS], on="siteCode", how="left")
    q = quality.validate_submissions(data.load_user_generated(), reference=data.research_points())
    cv_path = OUT / "cv_results.json"
    cv = json.load(open(cv_path)) if cv_path.exists() else None
    ins = insights.discover_all(merged, names, data.load_user_generated(), q.summary, cv)

    c = insights.counts(ins)
    print(f"Discovered {len(ins)} insights — {c['supported']} supported, "
          f"{c['exploratory']} exploratory, {c['rejected']} rejected.\n")
    for i in ins:
        print(f"[{i.challenge['status'].upper():11s}] {i.id}: {i.title}")
        print(f"            {i.finding}")
        print(f"            {i.challenge.get('detail','')}")
    with open(OUT / "insights.json", "w") as f:
        json.dump({"counts": c, "insights": [i.to_dict() for i in ins]}, f, indent=2)
    plan = planning.resample_plan(df, [i.to_dict() for i in ins])
    plan.to_csv(OUT / "campaign_plan.csv", index=False)
    print(f"\nNext campaign: {len(plan)} sites to re-sample in "
          f"{plan['city_name'].nunique()} cities.")
    print(f"Wrote {OUT/'insights.json'} and {OUT/'campaign_plan.csv'}")


if __name__ == "__main__":
    main()

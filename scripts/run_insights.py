"""Run the Insight Discovery Engine and save results.

Prints each discovered insight with its evidence and challenge outcome, and writes
outputs/insights.json. Run:  python scripts/run_insights.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, quality, insights, RISK_COMPONENTS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"
OUT.mkdir(exist_ok=True)


def main():
    df = data.build_analysis_table()
    df["composite_obs"] = df[RISK_COMPONENTS].mean(axis=1)
    feat_df, names = features.build_feature_matrix(df)
    merged = feat_df.merge(df[["siteCode"] + RISK_COMPONENTS], on="siteCode", how="left")
    q = quality.validate_submissions(data.load_user_generated())
    ins = insights.discover_all(merged, names, data.load_user_generated(), q.summary)

    surv = sum(i.challenge.get("survives") for i in ins)
    print(f"Discovered {len(ins)} insights — {surv} survived the challenge, {len(ins)-surv} weakened.\n")
    for i in ins:
        flag = "SURVIVES" if i.challenge.get("survives") else "WEAKENED"
        print(f"[{flag:9s}] {i.id}: {i.title}")
        print(f"            {i.challenge.get('detail','')}")
    with open(OUT / "insights.json", "w") as f:
        json.dump([i.to_dict() for i in ins], f, indent=2)
    print(f"\nWrote {OUT/'insights.json'}")


if __name__ == "__main__":
    main()

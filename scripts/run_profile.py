"""Step 1: load, profile, join-coverage table, and citizen data-quality report.

Prints real numbers and writes machine-readable outputs to outputs/.
Run:  python scripts/run_profile.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aquasentinel import data, quality, RISK_COMPONENTS, COMPOSITE  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"
OUT.mkdir(exist_ok=True)


def section(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def main():
    section("FILE PROFILE")
    loaders = {
        "cities": data.load_cities, "sites": data.load_sites,
        "health_risks": data.load_health_risks, "health_timeseries": data.load_health_timeseries,
        "nitrates": lambda: pd.read_csv(data.RAW_DIR / "nitrates.csv"),
        "urban_parameters": data.load_urban_parameters, "weather_summary": data.load_weather_summary,
        "user_generated": data.load_user_generated,
    }
    for name, fn in loaders.items():
        df = fn()
        print(f"  {name:20s} rows={len(df):4d}  cols={df.shape[1]:3d}")

    section("SITES PER CITY")
    sites = data.load_sites()
    print(sites.groupby("city_name").size().to_string())

    section("JOIN COVERAGE (True = site present in that file)")
    cov = data.coverage_table()
    cov.to_csv(OUT / "coverage_table.csv", index=False)
    counts = {c: int(cov[c].sum()) for c in cov.columns if c != "siteCode"}
    print(f"  Union of all site codes: {len(cov)}")
    for k, v in counts.items():
        print(f"    {k:20s} {v}")
    # sites missing risk targets
    missing_risk = cov[~cov["health_risks"]]["siteCode"].tolist()
    print(f"  Sites WITHOUT health_risks target: {len(missing_risk)} -> {missing_risk[:10]}")

    section("RISK TARGET STRUCTURE")
    hr = data.load_health_risks()
    recomputed = hr[RISK_COMPONENTS].mean(axis=1)
    max_err = (recomputed - hr[COMPOSITE]).abs().max()
    print(f"  Verifying composite == mean of 3 components: max abs error = {max_err:.6f}")
    print(hr[RISK_COMPONENTS + [COMPOSITE]].describe().round(3).to_string())
    top = hr.sort_values(COMPOSITE, ascending=False).head(5)
    print("\n  Top 5 highest-risk sites:")
    print(top[["researchSiteCode"] + RISK_COMPONENTS + [COMPOSITE]].round(3).to_string(index=False))

    section("NITRATE (mg/L)")
    nit = data.load_nitrates().merge(sites[["code", "city_name"]], left_on="siteCode", right_on="code")
    print(f"  range: {nit['nitrate_mgL'].min():.3f} - {nit['nitrate_mgL'].max():.3f}")
    print(nit.groupby("city_name")["nitrate_mgL"].mean().round(3).sort_values(ascending=False).to_string())

    section("CITIZEN DATA-QUALITY REPORT (user_generated_sites.csv)")
    ug = data.load_user_generated()
    res = quality.validate_submissions(ug)
    print(json.dumps(res.summary, indent=2))
    flagged = res.df[res.df["status"] == "REVIEW"][["userSiteCode", "name", "latitude", "longitude", "flags"]]
    print(f"\n  {len(flagged)} of {len(ug)} submissions flagged for review. Examples:")
    print(flagged.head(20).to_string(index=False))
    res.df.to_csv(OUT / "citizen_quality_report.csv", index=False)

    with open(OUT / "profile_summary.json", "w") as f:
        json.dump({
            "coverage": counts, "union_sites": len(cov),
            "sites_without_target": len(missing_risk),
            "composite_max_error": float(max_err),
            "risk_describe": hr[RISK_COMPONENTS + [COMPOSITE]].describe().round(4).to_dict(),
            "citizen_quality": res.summary,
        }, f, indent=2)
    print(f"\nWrote outputs/coverage_table.csv, citizen_quality_report.csv, profile_summary.json")


if __name__ == "__main__":
    main()

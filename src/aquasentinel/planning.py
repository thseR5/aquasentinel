"""Next-campaign planner — what new data would change each verdict.

The insight engine says what the current data supports. This module turns its
verdicts into a plan for the next sampling campaign:

  evidence_gaps   for each testable insight, how many sites a campaign would need
                  before the verdict could change (or why no number of sites would);
  resample_plan   the concrete sites to visit again, each with the insights it tests.

Sample sizes use the Fisher z-transform with the Fieller variance factor for
Spearman's rho, var(z) ~= 1.06 / (n - 3). They are planning estimates for site
counts at the current spread of conditions, not guarantees.
"""
from __future__ import annotations

import math

import pandas as pd

from . import RISK_COMPONENTS

SPEARMAN_VAR = 1.06        # Fieller, Hartley & Pearson (1957)
Z_POWER = 0.8416           # 80% power
Z_CI = 1.96                # two-sided 95% interval
EQUIV_RHO = 0.10           # "no meaningful link" margin for the ARG headline
NOT_WORTH_IT = 1000        # beyond this many sites a campaign cannot settle it

P, F, A = RISK_COMPONENTS

# Why a site is on the list, keyed by the insight that put it there.
REASONS = {
    "INS-ARG-01": "high ARG, missed by the composite",
    "INS-OUTLIER-01": "hotspot within its city",
    "INS-CONTRA-01": "composite hides one high component",
    "INS-SURPRISE-01": "high risk the landscape does not explain",
}


def sites_to_detect(rho: float, bar: float, n_now: int) -> int | None:
    """Sites needed for a within-city rho of this size to clear the family-wise bar
    with 80% power. The bar is |rho| at the 95th percentile of the best-of-N null at
    n_now; in z units that critical value does not depend on n, so it carries over."""
    if not rho or n_now <= 3:
        return None
    crit = math.atanh(bar) / math.sqrt(SPEARMAN_VAR / (n_now - 3))
    return int(math.ceil(3 + SPEARMAN_VAR * ((crit + Z_POWER) / math.atanh(abs(rho))) ** 2))


def sites_for_ci(half_width: float = EQUIV_RHO) -> int:
    """Sites needed for a 95% interval around rho ~= 0 to be +/- half_width wide."""
    return int(math.ceil(3 + SPEARMAN_VAR * (Z_CI / math.atanh(half_width)) ** 2))


def evidence_gaps(ins_list: list[dict]) -> list[dict]:
    """One row per testable insight: verdict now, what would change it, sites needed."""
    rows = []
    by_id = {i["id"]: i for i in ins_list}

    arg = by_id.get("INS-ARG-01")
    if arg:
        ev = arg["evidence"]
        bound = max(abs(v) for v in ev["ci95"])
        rows.append({
            "id": arg["id"], "insight": arg["title"], "verdict": arg["challenge"]["status"],
            "now": f"n = {ev['n']}: rules out a link stronger than |rho| ~ {bound:.2f}",
            "would_change": f"Narrow the interval to +/-{EQUIV_RHO:.2f}, or find a link "
                            f"outside it",
            "sites_needed": sites_for_ci(), "sites_now": ev["n"],
        })

    for i in ins_list:
        ch = i["challenge"]
        if i["kind"] != "association" or "within_city_rho" not in ch:
            continue
        rho, n_now = ch["within_city_rho"], ch.get("n") or i["evidence"]["n"]
        need = sites_to_detect(rho, ch.get("familywise_bar", 0.32), n_now)
        if need is None or need > NOT_WORTH_IT:
            change = (f"Within-city rho is {rho:+.2f}; more than {NOT_WORTH_IT:,} sites "
                      f"would be needed. Treat as closed.")
        elif ch["status"] == "rejected":
            change = (f"Within-city rho is only {rho:+.2f}; only a far larger network could "
                      f"revive it")
        else:
            change = (f"Hold a within-city rho of {rho:+.2f} on new sites until it clears "
                      f"the family-wise bar")
        rows.append({
            "id": i["id"], "insight": i["title"], "verdict": ch["status"],
            "now": f"n = {n_now}: within-city rho {rho:+.2f}",
            "would_change": change, "sites_needed": need, "sites_now": n_now,
        })

    for iid, change in [
        ("INS-CITY-01", "Sample one city again in a different season. Today every city "
                          "was sampled in a single campaign, so city and season are mixed."),
        ("INS-MODEL-01", "Add a sixth city and score the model on it before it is used for "
                         "anything."),
    ]:
        i = by_id.get(iid)
        if i:
            rows.append({"id": iid, "insight": i["title"], "verdict": i["challenge"]["status"],
                         "now": i["evidence"].get("metric", ""), "would_change": change,
                         "sites_needed": None, "sites_now": i["evidence"].get("n")})
    return rows


def resample_plan(df: pd.DataFrame, ins_list: list[dict]) -> pd.DataFrame:
    """Sites to visit again, each with every insight it would test.

    Sites tested by more insights come first, then higher ARG, then higher composite.
    """
    reasons: dict[str, list[str]] = {}
    for i in ins_list:
        if i["id"] in REASONS:
            for code in i["evidence"].get("sites", []):
                reasons.setdefault(code, []).append(REASONS[i["id"]])
    cols = ["siteCode", "name", "city_name", "samplingDate"] + RISK_COMPONENTS
    lab = df.dropna(subset=RISK_COMPONENTS)
    plan = lab[lab["siteCode"].isin(reasons)][[c for c in cols if c in lab.columns]].copy()
    plan["composite"] = plan[RISK_COMPONENTS].mean(axis=1)
    plan["reasons"] = plan["siteCode"].map(lambda c: "; ".join(reasons[c]))
    plan["n_reasons"] = plan["siteCode"].map(lambda c: len(reasons[c]))
    return (plan.sort_values(["n_reasons", A, "composite"], ascending=False)
            .reset_index(drop=True))

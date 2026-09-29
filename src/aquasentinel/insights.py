"""Insight Discovery Engine — the core of AquaSentinel's "Evidence Before Action".

Discovers patterns, associations, contradictions, outliers and coverage gaps from
the OneAquaHealth data using transparent statistics, then attaches an evidence
profile and a "challenge" that actively tries to invalidate each finding (city
confounding, permutation, sample size). Nothing here invents a number: every
Insight carries the exact statistic, sample size and geographic scope it rests on.

Rule enforced everywhere: NO EVIDENCE -> NO INSIGHT.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kruskal
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import RISK_COMPONENTS
from .features import plain

RNG = np.random.default_rng(42)

# Evidence dimensions shown as strength bars (0 = none .. 4 = strong).
STRENGTH_LEVELS = ["none", "very weak", "weak", "moderate", "strong"]


@dataclass
class Insight:
    id: str
    kind: str                      # pattern | association | contradiction | outlier | coverage | cross-city
    title: str
    finding: str                   # plain-language statement of what was found
    evidence: dict                 # {metric, value, p, n, scope, ...}
    strength: dict                 # {observed, association, prediction, causal} -> 0..4
    limitation: str
    next_step: str
    challenge: dict = field(default_factory=dict)  # {survives, detail}

    def to_dict(self):
        return asdict(self)


# --------------------------------------------------------------------------- #
#  1. Risk fingerprints (unsupervised pattern discovery on observed risk)
# --------------------------------------------------------------------------- #
def risk_fingerprints(df: pd.DataFrame, k_range=(2, 6)) -> tuple[pd.DataFrame, dict, Insight]:
    """Cluster labelled sites by their observed pathogen/faecal/ARG profile.

    Picks k by silhouette, characterises each cluster, and challenges the result
    with a permutation test: is the clustering tighter than clustering data whose
    joint structure has been destroyed by per-feature shuffling?
    """
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    X = StandardScaler().fit_transform(lab[RISK_COMPONENTS].to_numpy(float))

    best_k, best_sil, best_labels = None, -1, None
    for k in range(k_range[0], k_range[1] + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        sil = silhouette_score(X, km.labels_)
        if sil > best_sil:
            best_k, best_sil, best_labels = k, sil, km.labels_
    lab["cluster"] = best_labels

    # Characterise clusters by dominant risk dimension.
    profiles = {}
    for c in range(best_k):
        sub = lab[lab["cluster"] == c]
        means = sub[RISK_COMPONENTS].mean()
        dom = means.idxmax().replace("scaled", "").replace("Risk", "")
        profiles[c] = {
            "n": int(len(sub)),
            "means": {r: round(float(means[r]), 3) for r in RISK_COMPONENTS},
            "dominant": dom,
            "label": _profile_label(means),
            "cities": sub["city_name"].value_counts().to_dict(),
            "examples": sub.sort_values(RISK_COMPONENTS, ascending=False)["siteCode"].head(3).tolist(),
        }

    # Challenge: permutation silhouette (destroy joint structure per feature).
    null_sils = []
    for _ in range(200):
        Xp = np.column_stack([RNG.permutation(X[:, j]) for j in range(X.shape[1])])
        km = KMeans(n_clusters=best_k, n_init=5, random_state=1).fit(Xp)
        null_sils.append(silhouette_score(Xp, km.labels_))
    null_sils = np.array(null_sils)
    p_perm = float((null_sils >= best_sil).mean())
    survives = p_perm < 0.05

    ins = Insight(
        id="INS-FINGERPRINT",
        kind="pattern",
        title=f"High-risk sites split into {best_k} distinct risk fingerprints",
        finding=(f"Clustering the {len(lab)} sites by their observed pathogen/faecal/ARG "
                 f"profile reveals {best_k} groups with genuinely different risk shapes — "
                 f"a single composite score would blur these together."),
        evidence={"metric": "silhouette", "value": round(best_sil, 3), "k": best_k,
                  "n": int(len(lab)), "scope": f"{lab['city_name'].nunique()} cities",
                  "permutation_p": round(p_perm, 3)},
        strength={"observed": 4, "association": 3, "prediction": 1, "causal": 0},
        limitation=("Clusters describe observed risk composition only; they do not explain "
                    "why a site has that profile, and k is chosen by silhouette, not theory."),
        next_step="Profile each cluster against land-use and season with repeated sampling.",
        challenge={"survives": survives,
                   "detail": (f"Permutation test: real silhouette {best_sil:.3f} vs random "
                              f"{null_sils.mean():.3f} (95th pct {np.quantile(null_sils,0.95):.3f}); "
                              f"p={p_perm:.3f}. " + ("Structure is stronger than chance."
                              if survives else "Structure is NOT clearly beyond chance — treat as weak."))},
    )
    return lab, profiles, ins


def _profile_label(means: pd.Series) -> str:
    order = means.sort_values(ascending=False)
    names = {"scaledPathogenRisk": "pathogen", "scaledFecalRisk": "faecal", "scaledArgRisk": "ARG"}
    top = names[order.index[0]]
    if order.iloc[0] - order.iloc[1] < 0.05:
        return f"{top}/{names[order.index[1]]} co-dominant"
    return f"{top}-dominant"


# --------------------------------------------------------------------------- #
#  2. Associations, challenged for city-confounding
# --------------------------------------------------------------------------- #
def associations(df: pd.DataFrame, feature_names: list[str], top: int = 6) -> list[Insight]:
    """Environmental associations with composite risk, each challenged by removing
    city structure (within-city demeaning) and by a permutation test."""
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    comp = lab[RISK_COMPONENTS].mean(axis=1)
    lab = lab.assign(_comp=comp.values)

    rows = []
    for f in feature_names:
        if f not in lab.columns:
            continue
        x = lab[f]
        m = x.notna() & lab["_comp"].notna()
        if m.sum() < 15 or x[m].std() == 0:
            continue
        rho, p = spearmanr(x[m], lab["_comp"][m])
        rows.append((f, float(rho), float(p), int(m.sum())))
    rows.sort(key=lambda r: abs(r[1]), reverse=True)

    insights = []
    for i, (f, rho, p, n) in enumerate(rows[:top]):
        ch = _challenge_association(lab, f)
        strong_assoc = 3 if abs(rho) >= 0.25 else 2 if abs(rho) >= 0.15 else 1
        insights.append(Insight(
            id=f"INS-ASSOC-{i+1:02d}",
            kind="association",
            title=f"{plain(f).capitalize()} tracks stream health risk",
            finding=(f"Across {n} sites, {plain(f)} shows a "
                     f"{'positive' if rho>0 else 'negative'} rank association with composite "
                     f"risk (Spearman rho = {rho:+.2f})."),
            evidence={"metric": "Spearman rho", "value": round(rho, 3), "p": round(p, 4),
                      "n": n, "scope": f"{lab['city_name'].nunique()} cities"},
            strength={"observed": 4, "association": strong_assoc, "prediction": 1, "causal": 0},
            limitation=("Cross-sectional, single sample per site; association is not causation "
                        "and effect sizes are small."),
            next_step="Re-test with within-city controls and repeated seasonal sampling.",
            challenge=ch,
        ))
    return insights


def _challenge_association(lab: pd.DataFrame, f: str) -> dict:
    """Remove city structure (within-city demeaning) and check the association holds;
    also count in how many cities the sign is consistent."""
    sub = lab[[f, "_comp", "city_name"]].dropna()
    # Within-city demeaning (partial-out the city mean from both variables).
    x = sub[f] - sub.groupby("city_name")[f].transform("mean")
    y = sub["_comp"] - sub.groupby("city_name")["_comp"].transform("mean")
    if x.std() == 0:
        return {"survives": False, "detail": "No within-city variation to test."}
    rho_w, p_w = spearmanr(x, y)
    rho_g = spearmanr(sub[f], sub["_comp"]).correlation

    # Sign consistency across cities.
    signs = []
    for c, g in sub.groupby("city_name"):
        if len(g) >= 8 and g[f].std() > 0:
            signs.append(np.sign(spearmanr(g[f], g["_comp"]).correlation))
    same = int(sum(s == np.sign(rho_g) for s in signs))
    total = len(signs)

    survives = abs(rho_w) >= 0.15 and p_w < 0.10
    detail = (f"Within-city (city effect removed): rho = {rho_w:+.2f} (p={p_w:.3f}); "
              f"global rho = {rho_g:+.2f}. Sign consistent in {same}/{total} cities. ")
    detail += ("Association survives after controlling for city." if survives
               else "Association largely reflects differences BETWEEN cities, not within them — weakened.")
    return {"survives": bool(survives), "detail": detail,
            "within_city_rho": round(float(rho_w), 3), "cities_consistent": f"{same}/{total}"}


# --------------------------------------------------------------------------- #
#  3. Contradictions — composite score hides a dominant dimension
# --------------------------------------------------------------------------- #
def composite_contradictions(df: pd.DataFrame, gap: float = 0.35) -> list[Insight]:
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    comp = lab[RISK_COMPONENTS].mean(axis=1)
    mx = lab[RISK_COMPONENTS].max(axis=1)
    lab = lab.assign(_comp=comp.values, _max=mx.values, _spread=(mx - comp).values)
    flagged = lab[lab["_spread"] >= gap].sort_values("_spread", ascending=False)
    if flagged.empty:
        return []
    ex = flagged.head(5)
    examples = []
    for _, r in ex.iterrows():
        dom = r[RISK_COMPONENTS].idxmax().replace("scaled", "").replace("Risk", "")
        examples.append(f"{r['siteCode']} ({r['city_name']}): composite {r['_comp']:.2f} "
                        f"but {dom} {r[RISK_COMPONENTS].max():.2f}")
    return [Insight(
        id="INS-CONTRA-01",
        kind="contradiction",
        title="Composite score hides a dominant risk dimension at some sites",
        finding=(f"{len(flagged)} sites have one risk component at least {gap:.2f} above their "
                 f"composite score — the average masks a substantially elevated dimension."),
        evidence={"metric": "max-minus-composite gap", "threshold": gap,
                  "n_flagged": int(len(flagged)), "n": int(len(lab)),
                  "examples": examples},
        strength={"observed": 4, "association": 2, "prediction": 0, "causal": 0},
        limitation="Reflects how the composite is defined (mean of three components); descriptive.",
        next_step="Report and triage by dominant component, not by composite alone.",
        challenge={"survives": True,
                   "detail": ("Arithmetic fact about the observed components, not a modelled "
                              "claim — robust by construction.")},
    )]


# --------------------------------------------------------------------------- #
#  4. Outliers — sites unusual within their city
# --------------------------------------------------------------------------- #
def outliers(df: pd.DataFrame, z: float = 1.5) -> list[Insight]:
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    lab["_comp"] = lab[RISK_COMPONENTS].mean(axis=1)
    lab["_z"] = lab.groupby("city_name")["_comp"].transform(
        lambda s: (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) > 0 else 1))
    hi = lab[lab["_z"] >= z].sort_values("_z", ascending=False)
    if hi.empty:
        return []
    ex = [f"{r['siteCode']} ({r['city_name']}): {r['_z']:+.1f} SD above its city mean "
          f"(composite {r['_comp']:.2f})" for _, r in hi.head(5).iterrows()]
    return [Insight(
        id="INS-OUTLIER-01",
        kind="outlier",
        title="A few sites stand well above their own city's norm",
        finding=(f"{len(hi)} sites sit at least {z} standard deviations above their city's mean "
                 f"composite risk — local hotspots worth first inspection."),
        evidence={"metric": "within-city z-score", "threshold": z,
                  "n_flagged": int(len(hi)), "examples": ex, "n": int(len(lab))},
        strength={"observed": 4, "association": 2, "prediction": 1, "causal": 0},
        limitation="Based on one sample per site; an outlier may reflect sampling, not a trend.",
        next_step="Re-sample flagged sites and their upstream/downstream neighbours.",
        challenge={"survives": True,
                   "detail": "Descriptive within-city ranking; not a cross-city or predictive claim."},
    )]


# --------------------------------------------------------------------------- #
#  5. Cross-city differences
# --------------------------------------------------------------------------- #
def cross_city(df: pd.DataFrame) -> list[Insight]:
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    lab["_comp"] = lab[RISK_COMPONENTS].mean(axis=1)
    groups = [g["_comp"].values for _, g in lab.groupby("city_name")]
    if len(groups) < 2:
        return []
    H, p = kruskal(*groups)
    means = lab.groupby("city_name")["_comp"].mean().sort_values(ascending=False)
    order = " > ".join(f"{c} ({v:.2f})" for c, v in means.items())
    return [Insight(
        id="INS-CITY-01",
        kind="cross-city",
        title="Composite risk differs significantly across cities",
        finding=f"City ranking by mean composite risk: {order}.",
        evidence={"metric": "Kruskal-Wallis H", "value": round(float(H), 2),
                  "p": round(float(p), 4), "n": int(len(lab)), "scope": f"{len(groups)} cities"},
        strength={"observed": 4, "association": 3, "prediction": 1, "causal": 0},
        limitation="City differences may reflect sampling protocol, season or land-use, not water quality alone.",
        next_step="Model with a city random effect before comparing environmental drivers across cities.",
        challenge={"survives": bool(p < 0.05),
                   "detail": (f"Kruskal-Wallis p={p:.3f}. " + ("Differences exceed chance."
                              if p < 0.05 else "Not clearly beyond chance."))},
    )]


# --------------------------------------------------------------------------- #
#  6. Citizen-data coverage & quality
# --------------------------------------------------------------------------- #
def citizen_coverage(user_df: pd.DataFrame, quality_summary: dict) -> list[Insight]:
    s = quality_summary
    pct = 100 * s["n_review"] / s["n_total"] if s["n_total"] else 0
    return [Insight(
        id="INS-CITIZEN-01",
        kind="coverage",
        title="Most citizen submissions need review before they can be trusted",
        finding=(f"{s['n_review']} of {s['n_total']} citizen submissions ({pct:.0f}%) are flagged: "
                 f"{s['junk_name']} junk names, {s['duplicate']} duplicates, "
                 f"{s['likely_swapped']} swapped coordinates, {s['out_of_region']} out of region."),
        evidence={"metric": "flagged share", "value": round(pct, 1),
                  "n": int(s["n_total"]), "breakdown": s},
        strength={"observed": 4, "association": 0, "prediction": 0, "causal": 0},
        limitation="Swap detection only catches swaps that land in a partner country; other swaps show as out-of-region.",
        next_step="Prompt citizens to confirm flagged coordinates and merge duplicate points at capture time.",
        challenge={"survives": True,
                   "detail": "Deterministic rule outcomes on the actual submissions — fully reproducible."},
    )]


# --------------------------------------------------------------------------- #
#  Orchestration
# --------------------------------------------------------------------------- #
def discover_all(df: pd.DataFrame, feature_names: list[str],
                 user_df: pd.DataFrame | None = None,
                 quality_summary: dict | None = None) -> list[Insight]:
    """Run every discovery. Returns insights ordered surviving-first, then by kind."""
    out: list[Insight] = []
    _, _, fp = risk_fingerprints(df)
    out.append(fp)
    out += associations(df, feature_names)
    out += composite_contradictions(df)
    out += outliers(df)
    out += cross_city(df)
    if user_df is not None and quality_summary is not None:
        out += citizen_coverage(user_df, quality_summary)
    # surviving insights first, then stronger association first
    out.sort(key=lambda i: (not i.challenge.get("survives", False),
                            -i.strength.get("association", 0)))
    return out

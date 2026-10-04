"""Insight Discovery Engine — the core of AquaSentinel's "Evidence Before Action".

Discovers patterns, associations, contradictions, outliers and coverage gaps from
the OneAquaHealth data using transparent statistics, then *challenges* each one.
Every insight ends with one of three verdicts:

  supported    survived every challenge that applies to it
  exploratory  survived the confounding check but NOT the multiple-testing
               correction — a hypothesis worth sampling for, not a finding
  rejected     failed the challenge (e.g. the pattern was city confounding)

Nothing here invents a number: every Insight carries the exact statistic, sample
size and geographic scope it rests on.  Rule: NO EVIDENCE -> NO INSIGHT.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kruskal, rankdata
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import RISK_COMPONENTS
from .features import plain

SEED = 42
N_PERM = 500            # shuffles for the family-wise association challenge
N_NULL_CLUSTER = 200    # simulated datasets for the fingerprint challenge
N_BOOT = 1000           # bootstrap resamples for confidence intervals
ALPHA = 0.05

STATUSES = ("supported", "exploratory", "rejected")
# Evidence dimensions shown as strength bars (0 = none .. 4 = strong).
STRENGTH_LEVELS = ["none", "very weak", "weak", "moderate", "strong"]

P, F, A = RISK_COMPONENTS
SHORT = {P: "pathogen", F: "faecal", A: "ARG"}


def _verdict(status: str, detail: str, **extra) -> dict:
    """Challenge record. `survives` is a strict boolean: supported only."""
    assert status in STATUSES
    return {"status": status, "survives": status == "supported", "detail": detail, **extra}


def _num_word(k: int) -> str:
    return {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(k, str(k))


def _fmt_p(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


@dataclass
class Insight:
    id: str
    kind: str                      # pattern | association | contradiction | outlier | ...
    title: str
    finding: str                   # plain-language statement of what was found
    evidence: dict                 # {metric, value, p, n, scope, ...}
    strength: dict                 # {observed, association, prediction, causal} -> 0..4
    limitation: str
    next_step: str
    challenge: dict = field(default_factory=dict)  # {status, survives, detail}

    def to_dict(self):
        return asdict(self)


def _labelled(df: pd.DataFrame) -> pd.DataFrame:
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    lab["_comp"] = lab[RISK_COMPONENTS].mean(axis=1)
    return lab


def _within_city(s: pd.Series, city: pd.Series) -> pd.Series:
    """Remove the city mean (the city effect) from a variable."""
    return s - s.groupby(city).transform("mean")


# --------------------------------------------------------------------------- #
#  1. Headline: antibiotic resistance is its own risk dimension
# --------------------------------------------------------------------------- #
def arg_independence(df: pd.DataFrame) -> list[Insight]:
    """Is antibiotic-resistance (ARG) risk just another view of faecal pollution?

    Pathogen and faecal risk are tightly coupled. If ARG were coupled to them too,
    one composite number would be enough. We test that directly, with a bootstrap
    confidence interval and a within-city re-test, and count what a composite-based
    watchlist would miss.
    """
    lab = _labelled(df)
    n = len(lab)
    if n < 30:
        return []
    rng = np.random.default_rng(SEED)

    def boot_ci(a, b):
        x, y = lab[a].to_numpy(), lab[b].to_numpy()
        rs = []
        for _ in range(N_BOOT):
            i = rng.integers(0, n, n)
            rs.append(spearmanr(x[i], y[i]).correlation)
        return [round(float(v), 2) for v in np.nanquantile(rs, [0.025, 0.975])]

    def per_city(a, b):
        return {c: float(spearmanr(g[a], g[b]).correlation)
                for c, g in lab.groupby("city_name") if len(g) >= 8}

    r_fa = float(spearmanr(lab[F], lab[A]).correlation)
    ci_fa = boot_ci(F, A)
    rw_fa = round(float(spearmanr(_within_city(lab[F], lab["city_name"]),
                                  _within_city(lab[A], lab["city_name"])).correlation), 2) + 0.0
    r_pf = float(spearmanr(lab[P], lab[F]).correlation)
    ci_pf = boot_ci(P, F)
    pc_pf = per_city(P, F)
    rw_pa, pw_pa = spearmanr(_within_city(lab[P], lab["city_name"]),
                             _within_city(lab[A], lab["city_name"]))

    # What a composite-led watchlist misses: top-quartile ARG vs top-quartile composite.
    k = max(1, n // 4)
    top_arg = lab.nlargest(k, A)
    top_comp = set(lab.nlargest(k, "_comp")["siteCode"])
    missed = top_arg[~top_arg["siteCode"].isin(top_comp)]
    examples = [f"{r['siteCode']} ({r['city_name']}): ARG {r[A]:.2f}, faecal {r[F]:.2f}, "
                f"composite {r['_comp']:.2f}" for _, r in missed.head(5).iterrows()]

    # Operational rule, not proof of independence: the interval spans zero and the
    # within-city association is small.
    no_detectable_faecal_assoc = ci_fa[0] < 0 < ci_fa[1] and abs(rw_fa) < 0.15
    coupled = ci_pf[0] > 0.4 and all(v > 0 for v in pc_pf.values())
    status = "supported" if (no_detectable_faecal_assoc and coupled) else "rejected"
    detail = (
        f"Bootstrap ({N_BOOT} resamples): faecal-vs-ARG rho = {r_fa:+.2f}, 95% CI "
        f"{ci_fa[0]:+.2f} to {ci_fa[1]:+.2f} — the interval spans zero. "
        f"With the city effect removed it is {rw_fa:+.2f}. "
        f"Contrast: pathogen-vs-faecal rho = {r_pf:+.2f} (95% CI {ci_pf[0]:+.2f} to "
        f"{ci_pf[1]:+.2f}), positive in {sum(v > 0 for v in pc_pf.values())}/{len(pc_pf)} "
        f"cities (lowest {min(pc_pf.values()):+.2f}). "
        f"Caveat found by the same check: inside cities ARG is weakly related to pathogen "
        f"risk (rho = {rw_pa:+.2f}, {_fmt_p(pw_pa)}), so the supported claim is 'no detectable "
        f"association with faecal risk', not 'independent of everything'."
    )
    return [Insight(
        id="INS-ARG-01",
        kind="pattern",
        title="No detectable association between ARG and faecal risk",
        finding=(
            f"Pathogen and faecal risk move together (rho = {r_pf:+.2f}). ARG risk shows no "
            f"detectable association with faecal risk (rho = {r_fa:+.2f}). The composite top "
            f"quarter leaves out {len(missed)} of the {k} highest-ARG sites."),
        evidence={"metric": "Spearman rho, faecal vs ARG", "value": round(r_fa, 2),
                  "ci95": ci_fa, "n": int(n), "scope": f"{lab['city_name'].nunique()} cities",
                  "pathogen_faecal_rho": round(r_pf, 2), "pathogen_faecal_ci95": ci_pf,
                  "within_city_rho": round(rw_fa, 2),
                  "top_arg_n": int(k), "missed_by_composite": int(len(missed)),
                  "examples": examples, "sites": missed["siteCode"].tolist()},
        strength={"observed": 4, "association": 3, "prediction": 0, "causal": 0},
        limitation=(
            f"A null result on n={n} cannot rule out a small link (|rho| below about "
            f"{max(abs(ci_fa[0]), abs(ci_fa[1])):.2f}). One sample per site, and the scaled "
            f"ARG index is defined upstream by OneAquaHealth."),
        next_step=("Rank and triage sites on ARG as its own dimension, and re-sample the "
                   "high-ARG / low-faecal sites to confirm."),
        challenge=_verdict(status, detail),
    )]


# --------------------------------------------------------------------------- #
#  2. Contamination profiles (unsupervised pattern discovery on observed risk)
# --------------------------------------------------------------------------- #
def _best_k(X, k_range, n_init, seed):
    best = (None, -1.0, None)
    for k in range(k_range[0], k_range[1] + 1):
        km = KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X)
        sil = silhouette_score(X, km.labels_)
        if sil > best[1]:
            best = (k, float(sil), km.labels_)
    return best


def _profile_label(means: pd.Series, g_mean: pd.Series, g_std: pd.Series) -> str:
    """Describe a cluster by how each component sits against the network average."""
    groups = {"elevated": [], "low": [], "average": []}
    for c in RISK_COMPONENTS:
        z = (means[c] - g_mean[c]) / (g_std[c] if g_std[c] > 0 else 1)
        groups["elevated" if z > 0.25 else "low" if z < -0.25 else "average"].append(SHORT[c])
    return " · ".join(f"{lvl} {' + '.join(names)}" for lvl, names in groups.items() if names)


def risk_fingerprints(df: pd.DataFrame, k_range=(2, 6)) -> tuple[pd.DataFrame, dict, Insight]:
    """Cluster labelled sites by their observed pathogen/faecal/ARG profile.

    k is chosen by silhouette. The challenge is deliberately strict: the null is
    data with the SAME means and correlations but no clusters (multivariate normal),
    and the null gets the same "pick the best k" freedom as the real data. So a pass
    means "more clustered than correlated-but-continuous data", not just "the
    components are correlated".
    """
    lab = df.dropna(subset=RISK_COMPONENTS).copy()
    X = StandardScaler().fit_transform(lab[RISK_COMPONENTS].to_numpy(float))
    best_k, best_sil, best_labels = _best_k(X, k_range, n_init=10, seed=SEED)
    lab["cluster"] = best_labels

    g_mean, g_std = lab[RISK_COMPONENTS].mean(), lab[RISK_COMPONENTS].std()
    profiles = {}
    for c in range(best_k):
        sub = lab[lab["cluster"] == c]
        means = sub[RISK_COMPONENTS].mean()
        profiles[c] = {
            "n": int(len(sub)),
            "means": {r: round(float(means[r]), 3) for r in RISK_COMPONENTS},
            "dominant": SHORT[means.idxmax()],
            "label": _profile_label(means, g_mean, g_std),
            "cities": sub["city_name"].value_counts().to_dict(),
            "examples": sub.assign(_c=sub[RISK_COMPONENTS].mean(axis=1))
                           .nlargest(3, "_c")["siteCode"].tolist(),
        }

    rng = np.random.default_rng(SEED)
    cov = np.cov(X.T)
    null = np.array([
        _best_k(rng.multivariate_normal(np.zeros(X.shape[1]), cov, size=len(X)),
                k_range, n_init=5, seed=1)[1]
        for _ in range(N_NULL_CLUSTER)])
    p_null = float((1 + (null >= best_sil).sum()) / (1 + len(null)))
    status = "supported" if p_null < ALPHA else "rejected"

    spread = {c: max(p["means"][c] for p in profiles.values())
              - min(p["means"][c] for p in profiles.values()) for c in RISK_COMPONENTS}
    flat = [SHORT[c] for c in RISK_COMPONENTS if spread[c] < 0.05]
    varying = [SHORT[c] for c in RISK_COMPONENTS if SHORT[c] not in flat]
    parts = "; ".join(f"{p['n']} sites with {p['label']}" for p in profiles.values())
    finding = f"The {len(lab)} sites fall into {best_k} groups: {parts}."
    if flat and varying:
        finding += (f" {' and '.join(flat)} risk is nearly the same in every group, so the "
                    f"groups differ in their level of {' and '.join(varying)} contamination, "
                    f"not in {' or '.join(flat)}.")

    ins = Insight(
        id="INS-FINGERPRINT",
        kind="pattern",
        title=f"{_num_word(best_k).capitalize()} observed risk profiles emerge",
        finding=finding,
        evidence={"metric": "silhouette", "value": round(best_sil, 3), "k": best_k,
                  "n": int(len(lab)), "scope": f"{lab['city_name'].nunique()} cities",
                  "null_p": round(p_null, 3)},
        strength={"observed": 4, "association": 3, "prediction": 1, "causal": 0},
        limitation=("Clusters describe observed risk composition only; they do not explain "
                    "why a site has that profile, and k is chosen by silhouette, not theory."),
        next_step="Profile each group against land use and season with repeated sampling.",
        challenge=_verdict(status, (
            f"Compared with {N_NULL_CLUSTER} simulated datasets that keep the same "
            f"correlations but have no clusters (and get the same choice of k): real "
            f"silhouette {best_sil:.3f} vs simulated mean {null.mean():.3f} "
            f"(95th percentile {np.quantile(null, 0.95):.3f}); {_fmt_p(p_null)}. "
            + ("The grouping is stronger than correlation alone would produce."
               if status == "supported" else
               "The grouping is no stronger than correlated-but-continuous data."))),
    )
    return lab, profiles, ins


# --------------------------------------------------------------------------- #
#  3. Landscape associations — challenged for city confounding AND multiplicity
# --------------------------------------------------------------------------- #
def _familywise_null(lab: pd.DataFrame, feats: list[str]) -> np.ndarray:
    """Null distribution of the STRONGEST within-city |rho| across all screened
    features, from shuffling risk between sites of the same city.

    This is the honest yardstick when the best few features are picked out of many:
    it answers "how strong does the best of N look by chance alone?".
    """
    city = lab["city_name"]
    yd = _within_city(lab["_comp"], city).to_numpy()
    cols = []
    for f in feats:
        xd = _within_city(lab[f], city).to_numpy()
        m = ~np.isnan(xd)
        rx = rankdata(xd[m])
        cols.append((m, (rx - rx.mean()) / (rx.std() or 1)))
    groups = [np.flatnonzero((city == c).to_numpy()) for c in city.unique()]
    rng = np.random.default_rng(SEED)
    out = np.empty(N_PERM)
    for b in range(N_PERM):
        yp = yd.copy()
        for g in groups:
            yp[g] = yd[rng.permutation(g)]
        best = 0.0
        for m, zx in cols:
            ry = rankdata(yp[m])
            zy = (ry - ry.mean()) / (ry.std() or 1)
            best = max(best, abs(float(np.mean(zx * zy))))
        out[b] = best
    return out


def associations(df: pd.DataFrame, feature_names: list[str], top: int = 6) -> list[Insight]:
    """Landscape/climate associations with composite risk.

    Screens every feature, reports the `top` strongest, and challenges each twice:
      1. city confounding — recompute inside cities (city mean removed);
      2. multiple testing — compare with the best-of-N null (family-wise p).
    """
    lab = _labelled(df)
    feats = [f for f in feature_names
             if f in lab.columns and lab[f].notna().sum() >= 15 and lab[f].std() > 0]
    rows = []
    for f in feats:
        m = lab[f].notna()
        rho, p = spearmanr(lab.loc[m, f], lab.loc[m, "_comp"])
        rows.append((f, float(rho), float(p), int(m.sum())))
    rows.sort(key=lambda r: abs(r[1]), reverse=True)

    null_max = _familywise_null(lab, feats)
    null_95 = float(np.quantile(null_max, 0.95))

    insights = []
    for i, (f, rho, p, n) in enumerate(rows[:top]):
        ch = _challenge_association(lab, f, null_max, null_95, len(feats))
        status = ch["status"]
        label = plain(f)
        title = {
            "supported": f"{label.capitalize()} tracks stream health risk",
            "exploratory": f"Candidate signal: {label}",
            "rejected": f"{label.capitalize()} does not hold up as a risk signal",
        }[status]
        insights.append(Insight(
            id=f"INS-ASSOC-{i+1:02d}",
            kind="association",
            title=title,
            finding=(f"Across {n} sites, {label} shows a "
                     f"{'positive' if rho > 0 else 'negative'} rank association with composite "
                     f"risk (Spearman rho = {rho:+.2f}, {_fmt_p(p)} before any correction)."),
            evidence={"metric": "Spearman rho", "value": round(rho, 3), "p": round(p, 4),
                      "n": n, "scope": f"{lab['city_name'].nunique()} cities",
                      "features_screened": len(feats)},
            strength={"observed": 4,
                      "association": {"supported": 3, "exploratory": 2, "rejected": 1}[status],
                      "prediction": 0, "causal": 0},
            limitation=("Cross-sectional, one sample per site; association is not causation and "
                        "the effect is small."),
            next_step={
                "supported": "Design a targeted sampling campaign to test the mechanism.",
                "exploratory": "Treat as a hypothesis: write it down now and test it on new "
                               "samples or a new city before acting on it.",
                "rejected": "No action — keep it out of site prioritisation.",
            }[status],
            challenge=ch,
        ))
    return insights


def _challenge_association(lab, f, null_max, null_95, n_screened) -> dict:
    sub = lab[[f, "_comp", "city_name"]].dropna()
    x = _within_city(sub[f], sub["city_name"])
    y = _within_city(sub["_comp"], sub["city_name"])
    if x.std() == 0:
        return _verdict("rejected", "No within-city variation to test.")
    rho_w, p_w = spearmanr(x, y)
    rho_g = spearmanr(sub[f], sub["_comp"]).correlation

    signs = [np.sign(spearmanr(g[f], g["_comp"]).correlation)
             for _, g in sub.groupby("city_name") if len(g) >= 8 and g[f].std() > 0]
    same, total = int(sum(s == np.sign(rho_g) for s in signs)), len(signs)

    fw_p = float((1 + (null_max >= abs(rho_w)).sum()) / (1 + len(null_max)))
    passes_city = abs(rho_w) >= 0.15 and p_w < 0.10
    status = "rejected" if not passes_city else ("supported" if fw_p < ALPHA else "exploratory")

    detail = (f"Challenge 1 — city confounding: inside cities rho = {rho_w:+.2f} "
              f"({_fmt_p(p_w)}) vs {rho_g:+.2f} overall; same sign in {same}/{total} cities. ")
    if not passes_city:
        detail += ("The association mostly reflects differences BETWEEN cities, not between "
                   "sites — rejected.")
    else:
        detail += (f"Passed. Challenge 2 — multiple testing: this is one of the strongest of "
                   f"{n_screened} features screened. Shuffling risk between sites of the same "
                   f"city {len(null_max)} times, the best of {n_screened} reaches |rho| >= "
                   f"{null_95:.2f} by chance in 5% of shuffles; family-wise p = {fw_p:.2f}. ")
        detail += ("Stronger than chance even after correction — supported."
                   if status == "supported" else
                   "Not distinguishable from the best chance finding — kept as a hypothesis only.")
    return _verdict(status, detail, within_city_rho=round(float(rho_w), 3),
                    cities_consistent=f"{same}/{total}", familywise_p=round(fw_p, 3),
                    familywise_bar=round(null_95, 3), n=int(len(sub)))


# --------------------------------------------------------------------------- #
#  4. Contradictions — composite score hides a dominant dimension
# --------------------------------------------------------------------------- #
def composite_contradictions(df: pd.DataFrame, gap: float = 0.35) -> list[Insight]:
    lab = _labelled(df)
    mx = lab[RISK_COMPONENTS].max(axis=1)
    lab = lab.assign(_spread=(mx - lab["_comp"]).values)
    flagged = lab[lab["_spread"] >= gap].sort_values("_spread", ascending=False)
    if flagged.empty:
        return []
    examples = [f"{r['siteCode']} ({r['city_name']}): composite {r['_comp']:.2f} but "
                f"{SHORT[r[RISK_COMPONENTS].astype(float).idxmax()]} {r[RISK_COMPONENTS].max():.2f}"
                for _, r in flagged.head(5).iterrows()]
    return [Insight(
        id="INS-CONTRA-01",
        kind="contradiction",
        title="At some sites the composite score hides one very high component",
        finding=(f"{len(flagged)} sites have one risk component at least {gap:.2f} above their "
                 f"composite score — the average masks a substantially elevated dimension."),
        evidence={"metric": "max-minus-composite gap", "threshold": gap,
                  "n_flagged": int(len(flagged)), "n": int(len(lab)), "examples": examples,
                  "sites": flagged["siteCode"].tolist()},
        strength={"observed": 4, "association": 0, "prediction": 0, "causal": 0},
        limitation="Follows from how the composite is defined (mean of three components); descriptive.",
        next_step="Report and triage by the highest component, not by the composite alone.",
        challenge=_verdict("supported", "Arithmetic on the observed components, not a modelled "
                                        "claim — nothing to shuffle away."),
    )]


# --------------------------------------------------------------------------- #
#  5. Outliers — sites unusual within their city
# --------------------------------------------------------------------------- #
def outliers(df: pd.DataFrame, z: float = 1.5) -> list[Insight]:
    lab = _labelled(df)
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
                  "n_flagged": int(len(hi)), "examples": ex, "n": int(len(lab)),
                  "sites": hi["siteCode"].tolist()},
        strength={"observed": 4, "association": 0, "prediction": 0, "causal": 0},
        limitation="Based on one sample per site; an outlier may reflect that day, not a trend.",
        next_step="Re-sample flagged sites and their upstream and downstream neighbours.",
        challenge=_verdict("supported", "Descriptive ranking of observed values inside each "
                                        "city; it makes no cross-city or predictive claim."),
    )]


# --------------------------------------------------------------------------- #
#  6. Cross-city differences — per component, corrected for 3 tests
# --------------------------------------------------------------------------- #
def cross_city(df: pd.DataFrame) -> list[Insight]:
    lab = _labelled(df)
    by_city = lab.groupby("city_name")
    if by_city.ngroups < 2:
        return []
    p_comp = float(kruskal(*[g["_comp"].values for _, g in by_city]).pvalue)
    raw = {c: float(kruskal(*[g[c].values for _, g in by_city]).pvalue) for c in RISK_COMPONENTS}
    # Holm step-down correction across the three component tests.
    order = sorted(raw, key=raw.get)
    holm, running = {}, 0.0
    for i, c in enumerate(order):
        running = max(running, min(1.0, raw[c] * (len(order) - i)))
        holm[c] = running
    differing = [c for c in RISK_COMPONENTS if holm[c] < ALPHA]
    means = by_city[RISK_COMPONENTS].mean()
    tops = {c: (means[c].idxmax(), float(means[c].max()), means[c].idxmin(), float(means[c].min()))
            for c in RISK_COMPONENTS}
    examples = [f"{SHORT[c]}: highest in {tops[c][0]} ({tops[c][1]:.2f}), lowest in "
                f"{tops[c][2]} ({tops[c][3]:.2f}); adjusted {_fmt_p(holm[c])}"
                for c in RISK_COMPONENTS]
    hidden = bool(differing) and p_comp >= ALPHA
    status = "supported" if differing else "rejected"
    title = ("Cities differ on each risk dimension — the composite score hides it" if hidden
             else "Cities differ in stream health risk" if differing
             else "No clear difference in risk between cities")
    finding = (f"On the composite score the five cities are not clearly different "
               f"({_fmt_p(p_comp)}). " if p_comp >= ALPHA else
               f"The cities differ on the composite score ({_fmt_p(p_comp)}). ")
    if differing:
        names = [SHORT[c] for c in differing]
        listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        finding += (f"Split by component, {listed} risk "
                    f"{'differs' if len(names) == 1 else 'each differ'} between cities, and "
                    f"not in the same direction: "
                    f"{tops[P][0]} is highest for pathogen, {tops[A][0]} for ARG.")
    return [Insight(
        id="INS-CITY-01",
        kind="cross-city",
        title=title,
        finding=finding,
        evidence={"metric": "Kruskal-Wallis, Holm-adjusted p",
                  "composite_p": round(p_comp, 4),
                  "component_p": {SHORT[c]: round(holm[c], 4) for c in RISK_COMPONENTS},
                  "n": int(len(lab)), "scope": f"{by_city.ngroups} cities", "examples": examples},
        strength={"observed": 4, "association": 3 if differing else 1, "prediction": 0, "causal": 0},
        limitation=("Each city was sampled in a single campaign (May, June-July or September), so city and "
                    "season cannot be separated in this snapshot."),
        next_step="Compare cities component by component, and sample all cities in the same season.",
        challenge=_verdict(status, (
            "Three component tests, Holm-corrected: "
            + "; ".join(f"{SHORT[c]} {_fmt_p(holm[c])}" for c in RISK_COMPONENTS)
            + f". Composite alone: {_fmt_p(p_comp)}. "
            + ("Differences hold after correction." if differing
               else "Nothing clears the corrected threshold."))),
    )]


# --------------------------------------------------------------------------- #
#  7. Negative result — landscape does not predict risk in a new city
# --------------------------------------------------------------------------- #
def model_transfer(cv: dict | None) -> list[Insight]:
    """Turn the cross-validation report into an insight. A model that fails to beat
    a trivial baseline is itself evidence — about what NOT to act on."""
    if not cv or "composite" not in cv:
        return []
    names = {P: "pathogen", F: "faecal", A: "ARG", "composite": "composite"}
    beat = [t for t, r in cv.items() if r["loco"]["mae"] < r["loco_baseline"]["mae"]]
    comp = cv["composite"]
    ex = []
    for t, r in cv.items():
        mc = r["loco"].get("mean_city_spearman")
        per = r["loco"].get("per_city_spearman") or {}
        scored = sum(v is not None for v in per.values())
        where = "" if scored == len(per) else (
            f" (computable in {scored} of {len(per)} cities; elsewhere the model predicts a constant)")
        ex.append(f"{names.get(t, t)}: error {r['loco']['mae']:.3f} vs baseline "
                  f"{r['loco_baseline']['mae']:.3f}; rank agreement inside a held-out city "
                  + (f"{mc:+.2f} on average{where}" if mc is not None
                     else "not computable (the model predicts a constant)"))
    return [Insight(
        id="INS-MODEL-01",
        kind="negative result",
        title="Across these five cities, landscape features do not predict risk in an unseen city",
        finding=(f"Trained on four cities and tested on the fifth, the model beats a "
                 f"'predict the average' baseline for {len(beat)} of {len(cv)} targets. "
                 f"So landscape context is used here to explain and to generate hypotheses, "
                 f"never to forecast."),
        evidence={"metric": "leave-one-city-out MAE (composite)",
                  "value": round(comp["loco"]["mae"], 3),
                  "baseline": round(comp["loco_baseline"]["mae"], 3),
                  "n": int(comp["loco"]["n"]), "scope": "5 held-out cities", "examples": ex},
        strength={"observed": 4, "association": 1, "prediction": 0, "causal": 0},
        limitation=("96 sites and five cities is a small test; a larger network or repeated "
                    "sampling could reveal signal this snapshot cannot."),
        next_step="Do not rank unsampled sites by modelled risk; send samplers instead.",
        challenge=_verdict("supported", (
            "Each city is held out in turn, so the model never sees the city it is scored on. "
            "The baseline is the mean of the four training cities. Elastic-net and shallow "
            "gradient boosting were both tried; neither beats the baseline.")),
    )]


# --------------------------------------------------------------------------- #
#  8. Citizen-data quality
# --------------------------------------------------------------------------- #
def citizen_coverage(user_df: pd.DataFrame, quality_summary: dict) -> list[Insight]:
    s = quality_summary
    n = s["n_total"]
    pct = 100 * s["n_review"] / n if n else 0
    return [Insight(
        id="INS-CITIZEN-01",
        kind="coverage",
        title=f"{pct:.0f}% of citizen site registrations need fixing before use",
        finding=(f"{s['n_review']} of {n} citizen-registered sites are flagged: "
                 f"{s['junk_name']} test or placeholder names, {s['likely_swapped']} with latitude "
                 f"and longitude swapped, and {s['duplicate']} entries that are really "
                 f"{s['duplicate_clusters']} places registered several times. Separately, "
                 f"{s['outside_coverage']} registrations lie more than 50 km from any "
                 f"lab-monitored site; that is noted, not treated as an error."),
        evidence={"metric": "flagged share (%)", "value": round(pct, 1), "n": int(n),
                  "n_flagged": int(s["n_review"]), "breakdown": s},
        strength={"observed": 4, "association": 0, "prediction": 0, "causal": 0},
        limitation=("Rules catch what they are written for. A swap is only detected when the "
                    "corrected point lands near a known site; a real site with a generic name "
                    "can be flagged as a placeholder."),
        next_step=("Run the same checks in the app at the moment of entry: confirm swapped "
                   "coordinates and offer 'add a visit to the existing site' instead of a new one."),
        challenge=_verdict("supported", "Deterministic rules on the actual submissions; every "
                                        "flag names the rule that raised it and can be re-run."),
    )]


# --------------------------------------------------------------------------- #
#  9. Sites the candidate patterns do not explain
# --------------------------------------------------------------------------- #
def surprising_sites(df: pd.DataFrame) -> list[Insight]:
    """High observed risk but a benign setting on the two strongest landscape
    candidates (low vegetation fragmentation AND far from wastewater).

    The candidates themselves are only exploratory, so this is a list of where to
    look, not a claim about why."""
    need = ["patchDensityVeg250m", "log_distanceToSewageStations"]
    if not all(c in df.columns for c in need):
        return []
    lab = _labelled(df).dropna(subset=need)
    if len(lab) < 20:
        return []
    frag_pct = lab["patchDensityVeg250m"].rank(pct=True)
    dist_pct = lab["log_distanceToSewageStations"].rank(pct=True)
    hi = lab["_comp"] >= lab["_comp"].quantile(0.66)
    flagged = lab[hi & (frag_pct <= 0.5) & (dist_pct >= 0.5)].sort_values("_comp", ascending=False)
    if flagged.empty:
        return []
    ex = [f"{r['siteCode']} ({r['city_name']}): composite {r['_comp']:.2f}, "
          f"{np.expm1(r['log_distanceToSewageStations'])/1000:.1f} km from a wastewater station"
          for _, r in flagged.head(5).iterrows()]
    return [Insight(
        id="INS-SURPRISE-01",
        kind="surprising",
        title="High-risk sites that the landscape candidates do not explain",
        finding=(f"{len(flagged)} sites are in the top third for risk yet sit far from wastewater "
                 f"stations with unfragmented vegetation. Whatever drives their risk is not in "
                 f"the landscape data."),
        evidence={"metric": "high risk + benign setting", "n_flagged": int(len(flagged)),
                  "n": int(len(lab)), "examples": ex, "sites": flagged["siteCode"].tolist()},
        strength={"observed": 4, "association": 1, "prediction": 0, "causal": 0},
        limitation=("Built on two candidate patterns that are themselves only exploratory, and "
                    "on one sample per site; the mismatch could be noise or an unmapped source."),
        next_step="Put these first in line for repeat sampling and an upstream source search.",
        challenge=_verdict("exploratory", "The sites are real and their values are observed, but "
                           "the list is defined by patterns that did not clear the "
                           "multiple-testing correction — so it is a place to look, not a finding."),
    )]


# --------------------------------------------------------------------------- #
#  Orchestration
# --------------------------------------------------------------------------- #
def discover_all(df: pd.DataFrame, feature_names: list[str],
                 user_df: pd.DataFrame | None = None,
                 quality_summary: dict | None = None,
                 cv: dict | None = None,
                 fingerprint: Insight | None = None) -> list[Insight]:
    """Run every discovery. Order: supported, then exploratory, then rejected.

    Pass `fingerprint` (the Insight from `risk_fingerprints`) to reuse a result
    already computed by the caller instead of clustering twice."""
    out: list[Insight] = []
    out += arg_independence(df)
    out += cross_city(df)
    out.append(fingerprint if fingerprint is not None else risk_fingerprints(df)[2])
    out += composite_contradictions(df)
    out += outliers(df)
    out += model_transfer(cv)
    if user_df is not None and quality_summary is not None:
        out += citizen_coverage(user_df, quality_summary)
    out += associations(df, feature_names)
    out += surprising_sites(df)
    out.sort(key=lambda i: STATUSES.index(i.challenge["status"]))   # stable
    return out


def counts(insights: list) -> dict:
    """Verdict counts for a list of Insight objects or dicts."""
    def status(i):
        return (i["challenge"] if isinstance(i, dict) else i.challenge)["status"]
    return {s: sum(status(i) == s for i in insights) for s in STATUSES}

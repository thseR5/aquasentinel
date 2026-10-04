"""Risk modelling with honest validation for small tabular data (n<=96).

Core ideas:
  - Predict the three risk COMPONENTS (pathogen, fecal, ARG). Composite = mean.
  - Elastic-net (interpretable, handles collinear buffer families via L2 grouping).
  - Validate with LEAVE-ONE-CITY-OUT (does it transfer to a new city?) AND
    random K-fold, both against the simplest baseline: predict the mean of the
    training sites (for leave-one-city-out, the mean of the other four cities).
  - Report MAE, plus rank agreement computed INSIDE each held-out city. Pooling
    ranks across folds mixes in between-city offsets and overstates skill.
  - The model must beat baseline or we say it doesn't.
  - Split-conformal prediction intervals (valid for sites exchangeable with the
    calibration sites, i.e. the same five cities — not for a new city).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import sklearn
from scipy.stats import spearmanr
from sklearn.linear_model import ElasticNetCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from . import RISK_COMPONENTS

RANDOM_STATE = 42

# scikit-learn 1.7 renamed the size of the alpha grid (n_alphas -> alphas=int) and
# 1.9 removes the old name; support both so a fresh deploy never breaks.
_SK = tuple(int(x) for x in sklearn.__version__.split(".")[:2])
_ALPHA_GRID = {"alphas": 40} if _SK >= (1, 7) else {"n_alphas": 40}


def make_estimator() -> Pipeline:
    """Impute -> standardize -> elastic-net with inner CV for alpha & l1_ratio."""
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("enet", ElasticNetCV(
            l1_ratio=[0.2, 0.5, 0.9, 1.0],
            eps=1e-2, cv=5, max_iter=50000, tol=1e-3,
            n_jobs=-1, random_state=RANDOM_STATE, **_ALPHA_GRID,
        )),
    ])


def _metrics(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    mae = float(np.mean(np.abs(y_true - y_pred)))
    if np.std(y_pred) < 1e-9 or len(y_true) < 3:
        rho = float("nan")
    else:
        rho = float(spearmanr(y_true, y_pred).correlation)
    return {"mae": mae, "spearman": rho, "n": int(len(y_true))}


@dataclass
class CVReport:
    per_target: dict = field(default_factory=dict)

    def to_dict(self):
        return self.per_target


def _per_group_spearman(y, pred, groups) -> tuple[dict, float | None]:
    """Rank agreement inside each held-out group. None where predictions are flat."""
    per = {}
    for g in pd.unique(groups):
        m = groups == g
        if m.sum() < 3 or np.std(pred[m]) < 1e-9 or np.std(y[m]) < 1e-9:
            per[str(g)] = None
        else:
            per[str(g)] = float(spearmanr(y[m], pred[m]).correlation)
    vals = [v for v in per.values() if v is not None]
    return per, (float(np.mean(vals)) if vals else None)


def _run_folds(X, y, groups, fold_indices):
    """fold_indices: list of (train_idx, test_idx).
    Returns (model metrics, baseline metrics, pooled predictions, baseline predictions)."""
    preds = np.full(len(y), np.nan)
    base = np.full(len(y), np.nan)
    for tr, te in fold_indices:
        est = make_estimator()
        est.fit(X[tr], y[tr])
        preds[te] = est.predict(X[te])
        base[te] = y[tr].mean()  # baseline: predict the mean of the training sites
    mask = ~np.isnan(preds)
    m = _metrics(y[mask], preds[mask])
    b = _metrics(y[mask], base[mask])
    b["spearman"] = float("nan")   # a constant-per-fold baseline has no rank information
    if groups is not None:
        m["per_city_spearman"], m["mean_city_spearman"] = _per_group_spearman(y, preds, groups)
        m["pooled_spearman"] = m.pop("spearman")
    return m, b, preds, base


def leave_one_city_out(X, y, cities):
    idx = np.arange(len(y))
    folds = [(idx[cities != c], idx[cities == c]) for c in pd.unique(cities)]
    return _run_folds(X, y, cities, folds)


def kfold(X, y, k=5):
    from sklearn.model_selection import KFold
    kf = KFold(n_splits=k, shuffle=True, random_state=RANDOM_STATE)
    folds = list(kf.split(X))
    return _run_folds(X, y, None, folds)


def evaluate(feat_df: pd.DataFrame, target_df: pd.DataFrame, feature_names: list[str]) -> CVReport:
    """Full evaluation across the three components + composite, LOCO and K-fold."""
    df = feat_df.merge(target_df, on="siteCode", how="inner")
    df = df.dropna(subset=RISK_COMPONENTS)
    X = df[feature_names].to_numpy(dtype=float)
    cities = df["city_name"].to_numpy()

    report = CVReport()
    k = len(RISK_COMPONENTS)
    comp = {name: np.zeros(len(df)) for name in ("loco", "loco_base", "kf", "kf_base")}
    composite_true = df[RISK_COMPONENTS].mean(axis=1).to_numpy()

    for target in RISK_COMPONENTS:
        y = df[target].to_numpy(dtype=float)
        loco_m, loco_b, loco_pred, loco_base = leave_one_city_out(X, y, cities)
        kf_m, kf_b, kf_pred, kf_base = kfold(X, y)
        report.per_target[target] = {
            "loco": loco_m, "loco_baseline": loco_b,
            "kfold": kf_m, "kfold_baseline": kf_b,
        }
        comp["loco"] += loco_pred / k
        comp["loco_base"] += loco_base / k
        comp["kf"] += kf_pred / k
        comp["kf_base"] += kf_base / k

    # Composite = mean of the component predictions; its baseline is the mean of the
    # component baselines, so it never sees the held-out city either.
    loco_m = _metrics(composite_true, comp["loco"])
    loco_m["per_city_spearman"], loco_m["mean_city_spearman"] = _per_group_spearman(
        composite_true, comp["loco"], cities)
    loco_m["pooled_spearman"] = loco_m.pop("spearman")
    nan_rank = lambda d: {**d, "spearman": float("nan")}
    report.per_target["composite"] = {
        "loco": loco_m,
        "loco_baseline": nan_rank(_metrics(composite_true, comp["loco_base"])),
        "kfold": _metrics(composite_true, comp["kf"]),
        "kfold_baseline": nan_rank(_metrics(composite_true, comp["kf_base"])),
    }
    return report


@dataclass
class TrainedModel:
    estimators: dict           # target -> fitted Pipeline
    conformal_q: dict          # target (and "composite") -> 80% interval half-width
    feature_names: list
    coef_table: pd.DataFrame   # standardized coefficients per target
    train_stats: dict


def fit_full(feat_df, target_df, feature_names, alpha_interval=0.8) -> TrainedModel:
    """Fit on all labelled sites; compute split-conformal half-widths per target."""
    df = feat_df.merge(target_df, on="siteCode", how="inner").dropna(subset=RISK_COMPONENTS)
    X = df[feature_names].to_numpy(dtype=float)
    n = len(df)
    rng = np.random.default_rng(RANDOM_STATE)
    perm = rng.permutation(n)
    n_cal = max(15, n // 4)
    cal_idx, fit_idx = perm[:n_cal], perm[n_cal:]

    estimators, conformal_q, coefs = {}, {}, {}
    # Split conformal: the half-width is the ceil((n_cal+1)*coverage)/n_cal quantile of
    # the ABSOLUTE calibration residuals (already two-sided, so the level is the
    # coverage itself, with the finite-sample correction).
    q_level = min(1.0, np.ceil((n_cal + 1) * alpha_interval) / n_cal)
    cal_pred_sum = np.zeros(n_cal)
    for target in RISK_COMPONENTS:
        y = df[target].to_numpy(dtype=float)
        cal_est = make_estimator().fit(X[fit_idx], y[fit_idx])
        cal_pred = cal_est.predict(X[cal_idx])
        cal_pred_sum += cal_pred
        resid = np.abs(y[cal_idx] - cal_pred)
        conformal_q[target] = float(np.quantile(resid, q_level, method="higher"))
        full = make_estimator().fit(X, y)
        estimators[target] = full
        enet = full.named_steps["enet"]
        coefs[target] = enet.coef_

    # Composite interval from the composite's own calibration residuals.
    y_comp = df[RISK_COMPONENTS].mean(axis=1).to_numpy(dtype=float)
    comp_resid = np.abs(y_comp[cal_idx] - cal_pred_sum / len(RISK_COMPONENTS))
    conformal_q["composite"] = float(np.quantile(comp_resid, q_level, method="higher"))

    coef_table = pd.DataFrame(coefs, index=feature_names)
    coef_table["mean_abs"] = coef_table.abs().mean(axis=1)
    return TrainedModel(
        estimators=estimators, conformal_q=conformal_q, feature_names=feature_names,
        coef_table=coef_table.sort_values("mean_abs", ascending=False),
        train_stats={"n_train": int(n), "n_cal": int(n_cal)},
    )


def predict_site(model: TrainedModel, x_row: np.ndarray) -> dict:
    """Predict components + composite with conformal intervals for one site."""
    out = {}
    comp_vals = []
    for target in RISK_COMPONENTS:
        p = float(model.estimators[target].predict(x_row.reshape(1, -1))[0])
        p = min(max(p, 0.0), 1.0)
        q = model.conformal_q[target]
        out[target] = {"pred": p, "low": max(0.0, p - q), "high": min(1.0, p + q)}
        comp_vals.append(p)
    comp = float(np.mean(comp_vals))
    comp_q = float(model.conformal_q.get(
        "composite", np.mean([model.conformal_q[t] for t in RISK_COMPONENTS])))
    out["composite"] = {"pred": comp, "low": max(0.0, comp - comp_q), "high": min(1.0, comp + comp_q)}
    return out

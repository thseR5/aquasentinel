"""Risk modelling with honest validation for small tabular data (n<=96).

Core ideas:
  - Predict the three risk COMPONENTS (pathogen, fecal, ARG). Composite = mean.
  - Elastic-net (interpretable, handles collinear buffer families via L2 grouping).
  - Validate with LEAVE-ONE-CITY-OUT (does it transfer to a new city?) AND
    random K-fold, both against a city-mean / global-mean baseline.
  - Report MAE and Spearman; the model must beat baseline or we say it doesn't.
  - Split-conformal prediction intervals (distribution-free coverage).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import ElasticNetCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from . import RISK_COMPONENTS

RANDOM_STATE = 42


def make_estimator() -> Pipeline:
    """Impute -> standardize -> elastic-net with inner CV for alpha & l1_ratio."""
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("enet", ElasticNetCV(
            l1_ratio=[0.2, 0.5, 0.9, 1.0],
            n_alphas=40, cv=5, max_iter=5000, tol=1e-3,
            n_jobs=-1, random_state=RANDOM_STATE,
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


def _run_folds(X, y, groups, fold_indices):
    """fold_indices: list of (train_idx, test_idx). Returns pooled preds & baseline."""
    preds = np.full(len(y), np.nan)
    base = np.full(len(y), np.nan)
    for tr, te in fold_indices:
        est = make_estimator()
        est.fit(X[tr], y[tr])
        preds[te] = est.predict(X[te])
        base[te] = y[tr].mean()  # baseline: predict training mean
    mask = ~np.isnan(preds)
    return _metrics(y[mask], preds[mask]), _metrics(y[mask], base[mask]), preds


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
    composite_loco_pred = np.zeros(len(df))
    composite_kf_pred = np.zeros(len(df))
    composite_true = df[RISK_COMPONENTS].mean(axis=1).to_numpy()

    for target in RISK_COMPONENTS:
        y = df[target].to_numpy(dtype=float)
        loco_m, loco_base, loco_pred = leave_one_city_out(X, y, cities)
        kf_m, kf_base, kf_pred = kfold(X, y)
        report.per_target[target] = {
            "loco": loco_m, "loco_baseline": loco_base,
            "kfold": kf_m, "kfold_baseline": kf_base,
        }
        composite_loco_pred += np.nan_to_num(loco_pred)
        composite_kf_pred += np.nan_to_num(kf_pred)

    composite_loco_pred /= len(RISK_COMPONENTS)
    composite_kf_pred /= len(RISK_COMPONENTS)
    base_val = composite_true.mean()
    report.per_target["composite"] = {
        "loco": _metrics(composite_true, composite_loco_pred),
        "loco_baseline": _metrics(composite_true, np.full_like(composite_true, base_val)),
        "kfold": _metrics(composite_true, composite_kf_pred),
        "kfold_baseline": _metrics(composite_true, np.full_like(composite_true, base_val)),
    }
    return report


@dataclass
class TrainedModel:
    estimators: dict           # target -> fitted Pipeline
    conformal_q: dict          # target -> residual quantile (80% interval half-width)
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
    q_level = alpha_interval + (1 - alpha_interval) / 2  # e.g. 0.9 for 80% two-sided
    for target in RISK_COMPONENTS:
        y = df[target].to_numpy(dtype=float)
        cal_est = make_estimator().fit(X[fit_idx], y[fit_idx])
        resid = np.abs(y[cal_idx] - cal_est.predict(X[cal_idx]))
        conformal_q[target] = float(np.quantile(resid, q_level))
        full = make_estimator().fit(X, y)
        estimators[target] = full
        enet = full.named_steps["enet"]
        coefs[target] = enet.coef_

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
    comp_q = float(np.mean([model.conformal_q[t] for t in RISK_COMPONENTS]))
    out["composite"] = {"pred": comp, "low": max(0.0, comp - comp_q), "high": min(1.0, comp + comp_q)}
    return out

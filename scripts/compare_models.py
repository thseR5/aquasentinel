"""Secondary check: does shallow gradient boosting beat elastic-net / baseline?

Reports composite-risk LOCO and K-fold MAE/Spearman for a shallow
HistGradientBoosting model vs the training-mean baseline (per fold). Kept separate so the main
analysis stays fast. Result feeds the model card's honesty section.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, RISK_COMPONENTS  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"


def gbm():
    return HistGradientBoostingRegressor(
        max_depth=2, max_iter=150, learning_rate=0.05,
        l2_regularization=1.0, min_samples_leaf=8, random_state=42,
    )


def metrics(yt, yp):
    yt, yp = np.asarray(yt), np.asarray(yp)
    rho = spearmanr(yt, yp).correlation if np.std(yp) > 1e-9 else float("nan")
    return {"mae": float(np.mean(np.abs(yt - yp))), "spearman": float(rho)}


def main():
    df = data.build_analysis_table()
    feat_df, feats = features.build_feature_matrix(df)
    tdf = df[["siteCode"] + RISK_COMPONENTS]
    d = feat_df.merge(tdf, on="siteCode").dropna(subset=RISK_COMPONENTS)
    X = d[feats].to_numpy(float)
    cities = d["city_name"].to_numpy()
    ycomp = d[RISK_COMPONENTS].mean(axis=1).to_numpy()

    # component-wise preds averaged to composite
    def cv_preds(folds):
        pred, base = np.zeros(len(d)), np.zeros(len(d))
        for t in RISK_COMPONENTS:
            y = d[t].to_numpy(float)
            p, b = np.zeros(len(d)), np.zeros(len(d))
            for tr, te in folds:
                m = gbm().fit(X[tr], y[tr])
                p[te] = m.predict(X[te])
                b[te] = y[tr].mean()          # baseline never sees the held-out fold
            pred += p
            base += b
        return pred / len(RISK_COMPONENTS), base / len(RISK_COMPONENTS)

    def city_rho(pred):
        rs = [spearmanr(ycomp[cities == c], pred[cities == c]).correlation
              for c in pd.unique(cities) if np.std(pred[cities == c]) > 1e-9]
        return float(np.mean(rs)) if rs else float("nan")

    idx = np.arange(len(d))
    loco = [(idx[cities != c], idx[cities == c]) for c in pd.unique(cities)]
    kf = list(KFold(5, shuffle=True, random_state=42).split(X))

    loco_pred, loco_base = cv_preds(loco)
    kf_pred, kf_base = cv_preds(kf)
    mae = lambda yp: float(np.mean(np.abs(ycomp - yp)))
    res = {
        "gbm_loco": {"mae": mae(loco_pred), "mean_city_spearman": city_rho(loco_pred)},
        "loco_baseline": {"mae": mae(loco_base)},
        "gbm_kfold": {"mae": mae(kf_pred), "spearman": metrics(ycomp, kf_pred)["spearman"]},
        "kfold_baseline": {"mae": mae(kf_base)},
    }
    print(json.dumps(res, indent=2))
    with open(OUT / "gbm_comparison.json", "w") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    main()

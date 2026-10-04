"""Step 2: analysis + modelling. Computes real numbers, saves model & figures.

Run:  python scripts/run_analysis.py
Outputs: outputs/cv_results.json, spearman_signals.csv, coefficients.csv,
         model.joblib, and figures in outputs/figures/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aquasentinel import data, features, model, RISK_COMPONENTS, COMPOSITE  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
CB = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e"]  # colour-blind-safe


def section(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


def main():
    df = data.build_analysis_table()
    feat_df, feat_names = features.build_feature_matrix(df)
    target_df = df[["siteCode"] + RISK_COMPONENTS].copy()
    labelled = feat_df.merge(target_df, on="siteCode").dropna(subset=RISK_COMPONENTS)
    print(f"Features: {len(feat_names)} | labelled sites: {len(labelled)}")

    # ---- Spearman early-signal table (our own numbers) ----
    section("SPEARMAN SIGNALS vs composite risk (n, rho, p)")
    comp = labelled[RISK_COMPONENTS].mean(axis=1)
    sig_rows = []
    for f in feat_names:
        x = labelled[f]
        mask = x.notna() & comp.notna()
        if mask.sum() < 10 or x[mask].std() == 0:
            continue
        rho, p = spearmanr(x[mask], comp[mask])
        sig_rows.append({"feature": f, "plain": features.plain(f),
                         "n": int(mask.sum()), "rho": round(float(rho), 3), "p": round(float(p), 4)})
    sig = pd.DataFrame(sig_rows).sort_values("rho", key=lambda s: s.abs(), ascending=False)
    sig.to_csv(OUT / "spearman_signals.csv", index=False)
    print(sig.head(12).to_string(index=False))
    print("  ... (all effects are weak; strongest |rho| ~ {:.2f})".format(sig["rho"].abs().max()))

    # ---- Cross-validation (LOCO + K-fold vs baseline) ----
    section("CROSS-VALIDATION (LOCO = leave-one-city-out; must beat baseline)")
    report = model.evaluate(feat_df, target_df, feat_names)
    cv = report.to_dict()
    with open(OUT / "cv_results.json", "w") as f:
        json.dump(cv, f, indent=2)
    hdr = (f"{'target':20s} {'LOCO_MAE':>9s} {'base_MAE':>9s} {'city_rho':>9s} | "
           f"{'KF_MAE':>8s} {'base':>7s} {'KF_rho':>8s}")
    print(hdr); print("-" * len(hdr))
    for t, r in cv.items():
        mc = r["loco"]["mean_city_spearman"]
        print(f"{t:20s} {r['loco']['mae']:9.4f} {r['loco_baseline']['mae']:9.4f} "
              f"{(f'{mc:9.3f}' if mc is not None else '     flat')} | {r['kfold']['mae']:8.4f} "
              f"{r['kfold_baseline']['mae']:7.4f} {r['kfold']['spearman']:8.3f}")
    print("  city_rho = mean rank agreement INSIDE each held-out city ('flat' = constant predictions)")

    # ---- Fit full model + conformal, save ----
    section("FIT FULL MODEL + CONFORMAL INTERVALS")
    tm = model.fit_full(feat_df, target_df, feat_names)
    tm.coef_table.to_csv(OUT / "coefficients.csv")
    print(f"Trained on {tm.train_stats['n_train']} sites (calibration split {tm.train_stats['n_cal']}).")
    nz = {t: int((np.abs(tm.estimators[t].named_steps["enet"].coef_) > 1e-9).sum())
          for t in RISK_COMPONENTS}
    print("Non-zero coefficients per target:", nz)
    with open(OUT / "model_summary.json", "w") as f:
        json.dump({"nonzero_coefficients": nz,
                   "conformal_half_width_80": {k: round(v, 3) for k, v in tm.conformal_q.items()},
                   **tm.train_stats}, f, indent=2)
    print("Conformal 80% half-widths:", {k: round(v, 3) for k, v in tm.conformal_q.items()})
    print("\nTop 10 standardized drivers (mean |coef| across components):")
    print(tm.coef_table.head(10)[RISK_COMPONENTS + ["mean_abs"]].round(3).to_string())
    joblib.dump({"model": tm, "feature_names": feat_names}, OUT / "model.joblib")

    # ---- Figures ----
    # 1) Spearman signal bar
    top = sig.reindex(sig["rho"].abs().sort_values(ascending=False).index).head(12)[::-1]
    plt.figure(figsize=(7, 5))
    colors = [CB[0] if v > 0 else CB[1] for v in top["rho"]]
    plt.barh(top["plain"], top["rho"], color=colors)
    plt.axvline(0, color="#333", lw=0.8); plt.xlabel("Spearman rho vs composite risk")
    plt.title("Landscape drivers of stream health risk (weak, n=%d)" % len(labelled))
    plt.tight_layout(); plt.savefig(FIG / "spearman_signals.png", dpi=130); plt.close()

    # 2) LOCO predicted vs actual (composite)
    df2 = feat_df.merge(target_df, on="siteCode").dropna(subset=RISK_COMPONENTS)
    X = df2[feat_names].to_numpy(float); cities = df2["city_name"].to_numpy()
    _, _, comp_pred = _composite_loco(X, df2, feat_names)
    comp_true = df2[RISK_COMPONENTS].mean(axis=1).to_numpy()
    plt.figure(figsize=(6, 6))
    for i, c in enumerate(pd.unique(cities)):
        m = cities == c
        plt.scatter(comp_true[m], comp_pred[m], label=c, color=CB[i % len(CB)], s=40, alpha=0.8)
    lim = [0, max(comp_true.max(), comp_pred.max()) * 1.05]
    plt.plot(lim, lim, "--", color="#666"); plt.xlim(lim); plt.ylim(lim)
    plt.xlabel("Actual composite risk"); plt.ylabel("Predicted (leave-one-city-out)")
    plt.title("Transfer to unseen cities"); plt.legend()
    plt.tight_layout(); plt.savefig(FIG / "loco_pred_vs_actual.png", dpi=130); plt.close()

    # 3) coefficient bar for composite drivers
    ct = tm.coef_table.head(10).copy()
    ct["plain"] = [features.plain(i) for i in ct.index]
    ct = ct[::-1]
    plt.figure(figsize=(7, 5))
    plt.barh(ct["plain"], ct["mean_abs"], color=CB[2])
    plt.xlabel("Mean |standardized coefficient|"); plt.title("Model drivers (elastic-net)")
    plt.tight_layout(); plt.savefig(FIG / "model_drivers.png", dpi=130); plt.close()

    print(f"\nSaved figures to {FIG}")
    print("Wrote cv_results.json, spearman_signals.csv, coefficients.csv, model.joblib")


def _composite_loco(X, df2, feat_names):
    from aquasentinel.model import leave_one_city_out
    cities = df2["city_name"].to_numpy()
    pred = np.zeros(len(df2))
    for t in RISK_COMPONENTS:
        y = df2[t].to_numpy(float)
        _, _, p, _ = leave_one_city_out(X, y, cities)
        pred += np.nan_to_num(p)
    return None, None, pred / len(RISK_COMPONENTS)


if __name__ == "__main__":
    main()

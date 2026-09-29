"""AquaSentinel — One Health early-warning & insight platform for urban streams.

Single-file Streamlit app (robust for one-command deploy). Sections mirror the
feature priority list. Every screen states what the data can and cannot support.

Run:  streamlit run app/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aquasentinel import data, features, quality, explain, RISK_COMPONENTS, COMPOSITE  # noqa: E402
from aquasentinel.i18n import t, LANGS  # noqa: E402

import joblib  # noqa: E402

st.set_page_config(page_title="AquaSentinel", layout="wide")

# Colour-blind-safe risk palette (low->high).
RISK_COLORS = ["#2c7bb6", "#abd9e9", "#ffffbf", "#fdae61", "#d7191c"]
CB = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e"]
NITRATE_REF = 11.3  # EU Drinking Water Directive nitrate limit (mg/L NO3-N ~ indicative)


@st.cache_data(show_spinner=False)
def load_all():
    df = data.build_analysis_table()
    feat_df, feat_names = features.build_feature_matrix(df)
    df["composite_obs"] = df[RISK_COMPONENTS].mean(axis=1)
    return df, feat_df, feat_names


@st.cache_resource(show_spinner="Preparing risk model…")
def load_model():
    """Load the trained model artifact; rebuild it if missing or incompatible.

    On a fresh cloud deploy the pickled artifact may be absent, or a different
    scikit-learn version may refuse to unpickle it. In both cases we refit from
    the raw data (fast: three elastic-net fits, no cross-validation), so the app
    always has a working model without any manual build step.
    """
    path = ROOT / "outputs" / "model.joblib"
    if path.exists():
        try:
            return joblib.load(path)["model"]
        except Exception:
            pass  # version mismatch or corrupt -> rebuild below
    try:
        from aquasentinel.model import fit_full
        _df = data.build_analysis_table()
        _feat_df, _names = features.build_feature_matrix(_df)
        _targets = _df[["siteCode"] + RISK_COMPONENTS]
        return fit_full(_feat_df, _targets, _names)
    except Exception:
        return None


def risk_color(v: float) -> str:
    if pd.isna(v):
        return "#cccccc"
    bins = [0.15, 0.3, 0.45, 0.6]
    for i, b in enumerate(bins):
        if v < b:
            return RISK_COLORS[i]
    return RISK_COLORS[-1]


def risk_band(v: float) -> str:
    if pd.isna(v):
        return "unknown"
    return ["Low", "Low-moderate", "Moderate", "Elevated", "High"][
        min(4, sum(v >= b for b in [0.15, 0.3, 0.45, 0.6]))
    ]


df, feat_df, feat_names = load_all()
model = load_model()

# ------------------------------------------------------------------ sidebar
st.sidebar.title("AquaSentinel")
lang = st.sidebar.selectbox("Language / Idioma", list(LANGS.keys()),
                            format_func=lambda k: LANGS[k])
section = st.sidebar.radio(t("nav", lang), [
    t("overview", lang), t("map", lang), t("health_card", lang),
    t("drivers", lang), t("scenario", lang), t("copilot", lang),
    t("quality", lang), t("about", lang),
])
st.sidebar.caption(t("disclaimer", lang))

labelled = df.dropna(subset=RISK_COMPONENTS)


# ------------------------------------------------------------------ Overview
def page_overview():
    st.title(t("overview_title", lang))
    st.markdown(t("pitch", lang))
    c = st.columns(4)
    c[0].metric(t("cities", lang), df["city_name"].nunique())
    c[1].metric(t("sites", lang), len(df))
    c[2].metric(t("with_labs", lang), len(labelled))
    ug = quality.validate_submissions(data.load_user_generated())
    c[3].metric(t("flagged_pct", lang), f"{100*ug.summary['n_review']/ug.summary['n_total']:.0f}%")

    st.info(t("honesty_banner", lang))

    st.subheader(t("top_risk", lang))
    top = labelled.sort_values("composite_obs", ascending=False).head(10)
    show = top[["siteCode", "name", "city_name", "composite_obs"] + RISK_COMPONENTS].copy()
    show["band"] = show["composite_obs"].map(risk_band)
    show = show.rename(columns={"composite_obs": "composite"})
    st.dataframe(show.round(3), width='stretch', hide_index=True)


# ------------------------------------------------------------------ Map
def page_map():
    import folium
    from streamlit_folium import st_folium

    st.title(t("map_title", lang))
    layer = st.selectbox(t("layer", lang),
                         ["composite_obs"] + RISK_COMPONENTS + ["nitrate_mgL"])
    dd = df.dropna(subset=[layer]).copy()
    st.caption(f"{len(dd)} sites with values for **{layer}**.")

    # OpenStreetMap tiles are free and need no API key (CARTO basemaps now require one).
    m = folium.Map(location=[dd["latitude"].mean(), dd["longitude"].mean()],
                   zoom_start=5, tiles="OpenStreetMap")
    vmax = dd[layer].quantile(0.98) if layer == "nitrate_mgL" else 1.0
    for _, r in dd.iterrows():
        v = r[layer]
        color = risk_color(v / vmax if layer == "nitrate_mgL" else v)
        folium.CircleMarker(
            [r["latitude"], r["longitude"]], radius=6, color=color,
            fill=True, fill_color=color, fill_opacity=0.85, weight=1,
            popup=folium.Popup(
                f"<b>{r['siteCode']} — {r['name']}</b><br>{r['city_name']}<br>"
                f"{layer}: {v:.3f}<br>composite band: {risk_band(r.get('composite_obs'))}",
                max_width=250),
        ).add_to(m)
    st_folium(m, use_container_width=True, height=560, returned_objects=[])
    st.caption(t("map_caption", lang))


# ------------------------------------------------------------------ Health card
def page_health_card():
    st.title(t("card_title", lang))
    codes = labelled["siteCode"].tolist()
    default = codes.index("C5") if "C5" in codes else 0
    code = st.selectbox(t("select_site", lang), codes, index=default)
    row = df[df["siteCode"] == code].iloc[0]

    st.subheader(f"{row['siteCode']} — {row['name']}  ·  {row['city_name']}")
    cols = st.columns(4)
    comp = row["composite_obs"]
    cols[0].metric(t("composite", lang), f"{comp:.3f}", risk_band(comp))
    for i, comp_name in enumerate(RISK_COMPONENTS):
        cols[i + 1].metric(comp_name.replace("scaled", "").replace("Risk", ""),
                           f"{row[comp_name]:.3f}")

    # percentiles
    city_sites = labelled[labelled["city_name"] == row["city_name"]]
    pct_city = (city_sites["composite_obs"] < comp).mean() * 100
    pct_eu = (labelled["composite_obs"] < comp).mean() * 100
    st.write(t("percentile_line", lang).format(
        city=row["city_name"], pc=f"{pct_city:.0f}", pe=f"{pct_eu:.0f}"))

    # nitrate vs reference
    nit = row.get("nitrate_mgL")
    if pd.notna(nit):
        st.write(t("nitrate_line", lang).format(v=f"{nit:.2f}", ref=NITRATE_REF))

    # drivers (plain language) + honest note
    st.subheader(t("why", lang))
    if model is not None:
        x = feat_df[feat_df["siteCode"] == code][feat_names].to_numpy(float)
        drivers = explain.top_drivers_text(model, x[0], "composite", k=3)
        if drivers:
            for d_ in drivers:
                st.markdown(f"- {d_}")
        else:
            st.markdown(t("no_drivers", lang))
        pred = _predict(code)
        if pred:
            st.caption(t("model_est_line", lang).format(
                p=f"{pred['composite']['pred']:.2f}",
                lo=f"{pred['composite']['low']:.2f}",
                hi=f"{pred['composite']['high']:.2f}"))
    st.warning(t("card_honesty", lang))


def _predict(code):
    if model is None:
        return None
    from aquasentinel.model import predict_site
    x = feat_df[feat_df["siteCode"] == code][feat_names].to_numpy(float)
    if len(x) == 0:
        return None
    return predict_site(model, x[0])


# ------------------------------------------------------------------ Drivers & model
def page_drivers():
    st.title(t("drivers_title", lang))
    fig_dir = ROOT / "outputs" / "figures"
    st.subheader(t("associations", lang))
    if (fig_dir / "spearman_signals.png").exists():
        st.image(str(fig_dir / "spearman_signals.png"))
    sig_path = ROOT / "outputs" / "spearman_signals.csv"
    if sig_path.exists():
        st.dataframe(pd.read_csv(sig_path).head(12), width='stretch', hide_index=True)

    st.subheader(t("validation", lang))
    cv_path = ROOT / "outputs" / "cv_results.json"
    if cv_path.exists():
        import json
        cv = json.load(open(cv_path))
        rows = []
        for tgt, r in cv.items():
            rows.append({
                "target": tgt,
                "LOCO MAE": round(r["loco"]["mae"], 4),
                "baseline MAE": round(r["loco_baseline"]["mae"], 4),
                "beats baseline?": "yes" if r["loco"]["mae"] < r["loco_baseline"]["mae"] else "no",
                "LOCO Spearman": round(r["loco"]["spearman"], 3),
                "K-fold Spearman": round(r["kfold"]["spearman"], 3),
            })
        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
    if (fig_dir / "loco_pred_vs_actual.png").exists():
        st.image(str(fig_dir / "loco_pred_vs_actual.png"))
    st.error(t("model_honesty", lang))


# ------------------------------------------------------------------ Scenario
def page_scenario():
    st.title(t("scenario_title", lang))
    st.caption(t("scenario_caption", lang))
    if model is None:
        st.warning("Model artifact not found — run scripts/run_analysis.py first.")
        return
    codes = labelled["siteCode"].tolist()
    code = st.selectbox(t("base_site", lang), codes,
                        index=codes.index("C5") if "C5" in codes else 0)
    base_row = feat_df[feat_df["siteCode"] == code].copy()
    x = base_row[feat_names].to_numpy(float)[0].copy()

    st.markdown(t("adjust", lang))
    deltas = {}
    adjustable = {
        "imperviousPct1000m": "Impervious surface @1km (%)",
        "vegCoverFrac1000m": "Vegetation cover @1km (frac)",
        "log_distanceToSewageStations": "Distance to sewage station",
        "maxPrecipitationMm": "Peak rainfall (mm)",
    }
    for f, label in adjustable.items():
        if f not in feat_names:
            continue
        idx = feat_names.index(f)
        cur = float(x[idx])
        if f.startswith("log_"):
            pct = st.slider(f"{label} (% change)", -50, 50, 0, 5, key=f)
            deltas[idx] = np.log1p(np.expm1(cur) * (1 + pct / 100)) - cur
        else:
            pct = st.slider(f"{label} (% change)", -50, 50, 0, 5, key=f)
            deltas[idx] = cur * pct / 100

    from aquasentinel.model import predict_site
    base = predict_site(model, x)
    x2 = x.copy()
    for idx, dv in deltas.items():
        x2[idx] += dv
    scen = predict_site(model, x2)

    c = st.columns(2)
    c[0].metric(t("base_risk", lang), f"{base['composite']['pred']:.3f}",
                help=f"80% interval {base['composite']['low']:.2f}–{base['composite']['high']:.2f}")
    delta = scen['composite']['pred'] - base['composite']['pred']
    c[1].metric(t("scenario_risk", lang), f"{scen['composite']['pred']:.3f}",
                delta=f"{delta:+.3f}",
                help=f"80% interval {scen['composite']['low']:.2f}–{scen['composite']['high']:.2f}")

    # Alert rule: predicted composite above city 80th percentile
    city = df[df["siteCode"] == code]["city_name"].iloc[0]
    thr = labelled[labelled["city_name"] == city]["composite_obs"].quantile(0.8)
    if scen['composite']['pred'] > thr:
        st.error(t("alert_fire", lang).format(city=city, thr=f"{thr:.2f}"))
    else:
        st.success(t("alert_ok", lang).format(city=city, thr=f"{thr:.2f}"))
    st.info(t("scenario_honesty", lang))


# ------------------------------------------------------------------ Copilot
def page_copilot():
    st.title(t("copilot_title", lang))
    st.caption(t("copilot_caption", lang))
    c = st.columns(3)
    name = c[0].text_input(t("site_name", lang), "My Stream")
    lat = c[1].number_input("Latitude", value=40.20, format="%.5f")
    lon = c[2].number_input("Longitude", value=-8.42, format="%.5f")

    if st.button(t("check_btn", lang), type="primary"):
        sub = pd.DataFrame([{"name": name, "latitude": lat, "longitude": lon}])
        res = quality.validate_submissions(sub)
        row = res.df.iloc[0]
        st.subheader(t("step1_validation", lang))
        if row["status"] == "OK":
            st.success(t("validation_ok", lang))
        else:
            st.warning(f"{t('validation_flags', lang)} **{row['flags']}**")
            if row["suggestion"].get("swapped_latlon"):
                sl = row["suggestion"]["swapped_latlon"]
                st.info(t("swap_suggest", lang).format(lat=sl[0], lon=sl[1]))

        # nearest research site
        d2 = np.hypot(labelled["latitude"] - lat, labelled["longitude"] - lon)
        near = labelled.loc[d2.idxmin()]
        near_km = _haversine_km(lat, lon, near["latitude"], near["longitude"])
        st.subheader(t("step2_estimate", lang))
        st.write(t("nearest_line", lang).format(
            code=near["siteCode"], name=near["name"], km=f"{near_km:.1f}"))

        if near_km < 50 and model is not None:
            x = feat_df[feat_df["siteCode"] == near["siteCode"]][feat_names].to_numpy(float)[0]
            pred = _pred_x(x)
            band = risk_band(pred["composite"]["pred"])
            st.metric(t("est_band", lang), band,
                      f"{pred['composite']['pred']:.2f} "
                      f"({pred['composite']['low']:.2f}–{pred['composite']['high']:.2f})")
            drivers = explain.top_drivers_text(model, x, "composite", 3)
            st.write(t("est_explain", lang))
            for d_ in drivers or [t("no_drivers", lang)]:
                st.markdown(f"- {d_}")
            st.subheader(t("step3_action", lang))
            for a in _actions(band, lang):
                st.markdown(f"- {a}")
        else:
            st.info(t("too_far", lang))
        st.caption(t("copilot_guardrail", lang))


def _pred_x(x):
    from aquasentinel.model import predict_site
    return predict_site(model, x)


def _actions(band, lang):
    base = [t("action_sample", lang), t("action_report", lang)]
    if band in ("Elevated", "High"):
        return [t("action_avoid", lang)] + base + [t("action_notify", lang)]
    return base


def _haversine_km(a, b, c, d):
    import math
    r = 6371
    dphi = math.radians(c - a); dl = math.radians(d - b)
    x = (math.sin(dphi/2)**2 + math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dl/2)**2)
    return 2 * r * math.asin(math.sqrt(x))


# ------------------------------------------------------------------ Data quality
def page_quality():
    st.title(t("quality_title", lang))
    st.caption(t("quality_caption", lang))
    ug = data.load_user_generated()
    res = quality.validate_submissions(ug)
    s = res.summary
    cols = st.columns(5)
    cols[0].metric(t("submissions", lang), s["n_total"])
    cols[1].metric(t("needs_review", lang), s["n_review"])
    cols[2].metric("Junk names", s["junk_name"])
    cols[3].metric("Duplicates", s["duplicate"])
    cols[4].metric("Swapped/OOR", s["likely_swapped"] + s["out_of_region"])
    only = st.checkbox(t("show_flagged", lang), True)
    view = res.df[res.df["status"] == "REVIEW"] if only else res.df
    st.dataframe(view[["userSiteCode", "name", "latitude", "longitude", "flags"]],
                 width='stretch', hide_index=True)


# ------------------------------------------------------------------ About
def page_about():
    st.title(t("about_title", lang))
    st.markdown(t("about_body", lang))
    dd = ROOT / "docs" / "data_dictionary.md"
    if dd.exists():
        with st.expander("Data dictionary"):
            st.markdown(dd.read_text())


PAGES = {
    t("overview", lang): page_overview, t("map", lang): page_map,
    t("health_card", lang): page_health_card, t("drivers", lang): page_drivers,
    t("scenario", lang): page_scenario, t("copilot", lang): page_copilot,
    t("quality", lang): page_quality, t("about", lang): page_about,
}
PAGES[section]()

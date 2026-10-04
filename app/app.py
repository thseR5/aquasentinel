"""AquaSentinel — Evidence Before Action for urban stream health.

Single-file Streamlit app. The front door is the Insight feed: patterns found in
the OneAquaHealth data, each one challenged statistically and given a verdict
(supported / exploratory / rejected). Everything else supports that feed.

Run:  streamlit run app/app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aquasentinel import data, features, quality, explain, insights, planning, RISK_COMPONENTS  # noqa: E402
from aquasentinel.i18n import t, LANGS  # noqa: E402
from aquasentinel.insights import STRENGTH_LEVELS, STATUSES  # noqa: E402

import joblib  # noqa: E402

st.set_page_config(page_title="AquaSentinel", layout="wide")

P, F, A = RISK_COMPONENTS
SERIES = "#2a78d6"                      # single-series mark colour
PROFILE_COLORS = ["#1b9e77", "#d95f02"]  # validated colour-blind-safe pair
# Sequential ramp for magnitude on the map: one hue, light -> dark (low -> high).
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]
BANDS = [0.15, 0.30, 0.45, 0.60]
BAND_KEYS = ["band_low", "band_lowmod", "band_mod", "band_elev", "band_high"]
NITRATE_REF = 11.3   # 50 mg/L as nitrate = 11.3 mg/L as nitrate-nitrogen (EU drinking water)
NEAR_SITE_KM = 2.0   # a monitored site this close is worth showing to a citizen


# ------------------------------------------------------------------ data
@st.cache_data(show_spinner=False)
def load_all():
    df = data.build_analysis_table().copy()
    feat_df, feat_names = features.build_feature_matrix(df)
    df["composite_obs"] = df[RISK_COMPONENTS].mean(axis=1)
    return df, feat_df, feat_names


@st.cache_data(show_spinner=False)
def citizen_quality():
    return quality.validate_submissions(data.load_user_generated(),
                                        reference=data.research_points())


@st.cache_data(show_spinner=False)
def load_cv():
    path = ROOT / "outputs" / "cv_results.json"
    return json.load(open(path)) if path.exists() else None


@st.cache_data(show_spinner="Discovering and challenging insights…")
def discover():
    """Run the Insight Discovery Engine once and cache the result."""
    df = data.build_analysis_table()
    feat_df, names = features.build_feature_matrix(df)
    # Merge risk targets ONTO the feature frame so feature columns keep canonical names.
    merged = feat_df.merge(df[["siteCode"] + RISK_COMPONENTS], on="siteCode", how="left")
    q = citizen_quality()
    lab, profiles, fp = insights.risk_fingerprints(df)
    ins = insights.discover_all(merged, names, data.load_user_generated(), q.summary,
                                load_cv(), fingerprint=fp)
    return [i.to_dict() for i in ins], lab, profiles


@st.cache_resource(show_spinner=False)
def load_model():
    """Load the fitted model; refit from raw data if the pickle is missing or was
    written by an incompatible scikit-learn (fast: three elastic-net fits)."""
    path = ROOT / "outputs" / "model.joblib"
    if path.exists():
        try:
            return joblib.load(path)["model"]
        except Exception:
            pass
    try:
        from aquasentinel.model import fit_full
        _df = data.build_analysis_table()
        _feat_df, _names = features.build_feature_matrix(_df)
        return fit_full(_feat_df, _df[["siteCode"] + RISK_COMPONENTS], _names)
    except Exception:
        return None


def band_index(v: float) -> int:
    return int(sum(v >= b for b in BANDS))


def risk_color(v: float) -> str:
    return "#b8b8b8" if pd.isna(v) else RAMP[band_index(v)]


def risk_band(v: float, lang: str) -> str:
    return t("band_unknown", lang) if pd.isna(v) else t(BAND_KEYS[band_index(v)], lang)


def comp_name(c: str, lang: str) -> str:
    return t({P: "c_pathogen", F: "c_faecal", A: "c_arg", "composite_obs": "c_composite",
              "nitrate_mgL": "c_nitrate"}[c], lang)


df, feat_df, feat_names = load_all()
labelled = df.dropna(subset=RISK_COMPONENTS)

# ------------------------------------------------------------------ sidebar
st.sidebar.title("AquaSentinel")
st.sidebar.caption("Evidence Before Action")
lang = st.sidebar.selectbox("Language / Idioma", list(LANGS.keys()),
                            format_func=lambda k: LANGS[k])
MAIN = ["insight_feed", "plan", "watchlist", "fingerprints", "map"]
TOOLS = ["health_card", "citizen", "quality", "drivers", "about"]
mode = st.sidebar.radio(t("nav", lang), ["main", "tools"],
                        format_func=lambda m: t("mode_" + m, lang))
section = st.sidebar.radio(t("nav_page", lang), MAIN if mode == "main" else TOOLS,
                           format_func=lambda k: t(k, lang), label_visibility="collapsed")
st.sidebar.caption(t("principle", lang))
st.sidebar.caption(t("disclaimer", lang))


# ------------------------------------------------------------------ Insight feed
def _bar(level: int) -> str:
    return "█" * level + "░" * (4 - level)


BADGE = {"supported": (":green", "●"), "exploratory": (":orange", "◐"), "rejected": (":red", "✕")}


def render_evidence_card(ins: dict, gap: dict | None = None):
    status = ins["challenge"]["status"]
    color, icon = BADGE[status]
    with st.container(border=True):
        st.markdown(f"**{ins['title']}**  \n{color}[{icon} {t('st_' + status, lang)}] · "
                    f"`{ins['id']}` · {ins['kind']}")
        st.write(ins["finding"])
        ev = ins["evidence"]
        bits = []
        if "value" in ev:
            bits.append(f"{ev['metric']} = **{ev['value']}**")
        elif ev.get("metric"):
            bits.append(str(ev["metric"]))
        if ev.get("ci95"):
            bits.append(f"95% CI {ev['ci95'][0]:+.2f} to {ev['ci95'][1]:+.2f}")
        if ev.get("baseline") is not None:
            bits.append(f"baseline = {ev['baseline']}")
        if ev.get("p") is not None:
            bits.append(f"p = {ev['p']} ({t('uncorrected', lang)})")
        if ev.get("n"):
            bits.append(f"n = {ev['n']}")
        if ev.get("scope"):
            bits.append(str(ev["scope"]))
        if ev.get("n_flagged") is not None:
            bits.append(f"{ev['n_flagged']} {t('flagged', lang)}")
        st.caption(f"**{t('evidence_lbl', lang)}:** " + " · ".join(bits))
        for e in (ev.get("examples") or [])[:5]:
            st.markdown(f"   - {e}")
        s = ins["strength"]
        cols = st.columns(4)
        for col, key in zip(cols, ["observed", "association", "prediction", "causal"]):
            col.markdown(f"{t('dim_' + key, lang)}  \n`{_bar(s[key])}` {STRENGTH_LEVELS[s[key]]}")
        st.markdown(f"**{t('limitation_lbl', lang)}:** {ins['limitation']}")
        st.markdown(f"**{t('next_lbl', lang)}:** {ins['next_step']}")
        if gap:
            need = gap.get("sites_needed")
            extra = (f" ({t('sites_needed_fmt', lang).format(n=need, now=gap['sites_now'])})"
                     if need and need <= planning.NOT_WORTH_IT else "")
            st.markdown(f"**{t('change_lbl', lang)}:** {gap['would_change']}{extra}")
        with st.expander(t("challenge_lbl", lang)):
            st.write(ins["challenge"].get("detail", ""))


def _scatter(frame, x, y, title):
    """One-series scatter with a hover tooltip (site, city, both values)."""
    return (
        alt.Chart(frame, title=alt.Title(title, anchor="start", fontSize=14))
        .mark_circle(size=70, color=SERIES, opacity=0.75, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X(f"{x}:Q", title=comp_name(x, lang), scale=alt.Scale(domain=[0, 1])),
            y=alt.Y(f"{y}:Q", title=comp_name(y, lang), scale=alt.Scale(domain=[0, 1])),
            tooltip=[alt.Tooltip("siteCode:N", title=t("site", lang)),
                     alt.Tooltip("city_name:N", title=t("city", lang)),
                     alt.Tooltip(f"{x}:Q", title=comp_name(x, lang), format=".2f"),
                     alt.Tooltip(f"{y}:Q", title=comp_name(y, lang), format=".2f")])
        .properties(height=300)
        .configure_axis(gridColor="#e9eceb", domainColor="#c9cfcd", tickColor="#c9cfcd")
    )


def _rank_chart(k, missed):
    """Hero chart: every site placed by its composite rank and its ARG rank.
    The top-k ARG sites right of the dashed line are the ones a composite list misses."""
    r = labelled[["siteCode", "city_name", A, "composite_obs"]].copy()
    r["comp_rank"] = r["composite_obs"].rank(ascending=False, method="first")
    r["arg_rank"] = r[A].rank(ascending=False, method="first")
    groups = [t("rank_missed", lang).format(k=k), t("rank_caught", lang).format(k=k),
              t("rank_other", lang)]
    r["group"] = np.where(r["arg_rank"] > k, groups[2],
                          np.where(r["comp_rank"] > k, groups[0], groups[1]))
    pts = (alt.Chart(r)
           .mark_point(filled=True, size=80, opacity=0.9, stroke="white", strokeWidth=1)
           .encode(x=alt.X("comp_rank:Q", title=t("rank_comp", lang), scale=alt.Scale(domain=[1, len(r)])),
                   y=alt.Y("arg_rank:Q", title=t("rank_arg", lang),
                           scale=alt.Scale(domain=[1, len(r)], reverse=True)),
                   color=alt.Color("group:N", title=None, sort=groups,
                                   scale=alt.Scale(domain=groups, range=[SERIES, "#52514e", "#c9cfcd"]),
                                   legend=alt.Legend(orient="top")),
                   shape=alt.Shape("group:N", sort=groups, legend=None,
                                   scale=alt.Scale(domain=groups, range=["circle", "diamond", "circle"])),
                   tooltip=[alt.Tooltip("siteCode:N", title=t("site", lang)),
                            alt.Tooltip("city_name:N", title=t("city", lang)),
                            alt.Tooltip("arg_rank:Q", title=t("rank_arg", lang)),
                            alt.Tooltip("comp_rank:Q", title=t("rank_comp", lang)),
                            alt.Tooltip(f"{A}:Q", title=comp_name(A, lang), format=".2f"),
                            alt.Tooltip("composite_obs:Q", title=comp_name("composite_obs", lang),
                                        format=".2f")]))
    cut = pd.DataFrame({"v": [k + 0.5]})
    vline = alt.Chart(cut).mark_rule(color="#52514e", strokeDash=[4, 3]).encode(x="v:Q")
    hline = alt.Chart(cut).mark_rule(color="#52514e", strokeDash=[4, 3]).encode(y="v:Q")
    return ((hline + vline + pts)
            .properties(height=360, title=alt.Title(
                t("rank_chart", lang).format(missed=missed, k=k), anchor="start", fontSize=14))
            .configure_axis(gridColor="#e9eceb", domainColor="#c9cfcd", tickColor="#c9cfcd"))


def render_headline(ins_list):
    """The headline finding, drawn: who the composite misses, then why."""
    arg = next((i for i in ins_list if i["id"] == "INS-ARG-01"), None)
    if arg is None:
        return
    ev = arg["evidence"]
    with st.container(border=True):
        st.caption(t("headline_lbl", lang))
        st.subheader(t("headline_title", lang))
        st.markdown(t("headline_body", lang).format(
            missed=ev["missed_by_composite"], top=ev["top_arg_n"]))
        st.altair_chart(_rank_chart(ev["top_arg_n"], ev["missed_by_composite"]), width="stretch")
        st.markdown(f"**{t('why_lbl', lang)}**")
        cols = st.columns(2)
        frame = labelled[["siteCode", "city_name"] + RISK_COMPONENTS]
        cols[0].altair_chart(
            _scatter(frame, F, P, t("chart_pf", lang).format(r=f"{ev['pathogen_faecal_rho']:+.2f}")),
            width="stretch")
        cols[1].altair_chart(
            _scatter(frame, F, A, t("chart_fa", lang).format(r=f"{ev['value']:+.2f}")),
            width="stretch")
        st.caption(t("headline_caption", lang).format(
            lo=f"{ev['ci95'][0]:+.2f}", hi=f"{ev['ci95'][1]:+.2f}", n=ev["n"]))


def page_insight_feed():
    st.title(t("feed_title", lang))
    st.markdown(t("feed_intro", lang))
    ins_list, _, _ = discover()
    c = insights.counts(ins_list)
    downgraded = sum(i["kind"] == "association" and i["challenge"]["status"] == "exploratory"
                     for i in ins_list)
    screened = next((i["evidence"].get("features_screened") for i in ins_list
                     if i["kind"] == "association"), len(feat_names))
    st.markdown(t("tested_line", lang).format(n=len(ins_list), s=c["supported"],
                                              e=c["exploratory"], r=c["rejected"]))
    cols = st.columns(5)
    cols[0].metric(t("st_supported", lang), c["supported"])
    cols[1].metric(t("st_exploratory", lang), c["exploratory"])
    cols[2].metric(t("false_leads", lang), c["rejected"] + downgraded,
                   help=t("false_leads_help", lang).format(r=c["rejected"], d=downgraded, f=screened))
    cols[3].metric(t("sites", lang), len(df))
    cols[4].metric(t("with_labs", lang), len(labelled))

    render_headline(ins_list)

    st.subheader(t("all_insights", lang))
    st.caption(t("verdict_help", lang))
    pick = st.segmented_control(
        t("filter_verdict", lang), list(STATUSES), selection_mode="multi",
        default=list(STATUSES),
        format_func=lambda s: f"{t('st_' + s, lang)} ({c[s]})")
    gaps = {g["id"]: g for g in planning.evidence_gaps(ins_list)}
    for status in STATUSES:
        group = [i for i in ins_list if i["challenge"]["status"] == status]
        if status not in (pick or []) or not group:
            continue
        st.markdown(f"#### {t('grp_' + status, lang)}")
        if status == "rejected":
            st.caption(t("grp_rejected_note", lang))
        for ins in group:
            render_evidence_card(ins, gaps.get(ins["id"]))


# ------------------------------------------------------------------ Priority watchlist
def page_watchlist():
    st.title(t("watch_title", lang))
    st.markdown(t("watch_intro", lang))
    lab = labelled.copy()
    k = max(1, len(lab) // 4)
    dims = ["composite_obs", P, F, A]
    cols = st.columns([2, 1])
    dim = cols[0].segmented_control(t("rank_by", lang), dims, default=A,
                                    format_func=lambda d: comp_name(d, lang)) or A
    cities = sorted(lab["city_name"].unique())
    city = cols[1].selectbox(t("city", lang), [t("all_cities", lang)] + cities)

    top_comp = set(lab.nlargest(k, "composite_obs")["siteCode"])
    top = lab.nlargest(k, dim).copy()
    top["on_composite"] = top["siteCode"].isin(top_comp)
    n_missed = int((~top["on_composite"]).sum())
    z = lab.groupby("city_name")["composite_obs"].transform(
        lambda s: (s - s.mean()) / (s.std(ddof=0) or 1))
    top["city_hotspot"] = top.index.map(z >= 1.5)

    m = st.columns(3)
    m[0].metric(t("watch_n", lang), k, help=t("watch_n_help", lang))
    if dim != "composite_obs":
        m[1].metric(t("watch_missed", lang), f"{n_missed} / {k}", help=t("watch_missed_help", lang))
    m[2].metric(t("watch_hot", lang), int(top["city_hotspot"].sum()), help=t("watch_hot_help", lang))

    view = top if city == t("all_cities", lang) else top[top["city_name"] == city]
    yes, no = t("yes", lang), t("no", lang)
    table = pd.DataFrame({
        t("site", lang): view["siteCode"],
        t("site_name", lang): view["name"],
        t("city", lang): view["city_name"],
        comp_name(P, lang): view[P].round(2),
        comp_name(F, lang): view[F].round(2),
        comp_name(A, lang): view[A].round(2),
        comp_name("composite_obs", lang): view["composite_obs"].round(2),
        t("col_on_composite", lang): view["on_composite"].map({True: yes, False: no}),
        t("col_hotspot", lang): view["city_hotspot"].map({True: yes, False: no}),
        t("col_sampled", lang): view["samplingDate"].astype(str).str[:10],
    })
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button(t("download_watch", lang), table.to_csv(index=False).encode("utf-8"),
                       file_name=f"aquasentinel_watchlist_{dim}.csv", mime="text/csv")
    st.info(t("watch_honesty", lang))


# ------------------------------------------------------------------ Next campaign
def page_plan():
    st.title(t("plan_title", lang))
    st.markdown(t("plan_intro", lang))
    ins_list, _, _ = discover()
    plan = planning.resample_plan(df, ins_list)

    m = st.columns(4)
    m[0].metric(t("plan_sites", lang), len(plan), help=t("plan_sites_help", lang))
    m[1].metric(t("plan_multi", lang), int((plan["n_reasons"] >= 2).sum()))
    m[2].metric(t("plan_cities", lang), plan["city_name"].nunique())
    m[3].metric(t("plan_share", lang), f"{len(plan) / len(labelled):.0%}")

    st.subheader(t("plan_know", lang))
    gaps = pd.DataFrame(planning.evidence_gaps(ins_list))

    def needed(n):
        if pd.isna(n):
            return t("needs_design", lang)
        return t("closed", lang) if n > planning.NOT_WORTH_IT else f"{int(n):,}"

    st.dataframe(pd.DataFrame({
        t("col_insight", lang): gaps["insight"],
        t("col_verdict", lang): gaps["verdict"].map(lambda s: t("st_" + s, lang)),
        t("col_now", lang): gaps["now"],
        t("col_change", lang): gaps["would_change"],
        t("col_needed", lang): gaps["sites_needed"].map(needed),
    }), width="stretch", hide_index=True)

    reachable = gaps.dropna(subset=["sites_needed"])
    reachable = reachable[reachable["sites_needed"] <= planning.NOT_WORTH_IT]
    if not reachable.empty:
        bars = (alt.Chart(reachable, title=alt.Title(t("plan_chart", lang), anchor="start",
                                                     fontSize=14))
                .mark_bar(color=SERIES, cornerRadiusEnd=4, height=14)
                .encode(x=alt.X("sites_needed:Q", title=t("col_needed", lang),
                                scale=alt.Scale(type="log", domain=[50, 1000])),
                        y=alt.Y("insight:N", sort="x", title=None, axis=alt.Axis(labelLimit=360)),
                        tooltip=[alt.Tooltip("insight:N", title=t("col_insight", lang)),
                                 alt.Tooltip("sites_needed:Q", title=t("col_needed", lang)),
                                 alt.Tooltip("sites_now:Q", title="n")]))
        today = (alt.Chart(pd.DataFrame({"x": [len(labelled)]}))
                 .mark_rule(color="#52514e", strokeDash=[4, 3], strokeWidth=1.5)
                 .encode(x="x:Q"))
        st.altair_chart((bars + today).properties(height=34 * len(reachable) + 40)
                        .configure_axis(gridColor="#e9eceb", domainColor="#c9cfcd",
                                        tickColor="#c9cfcd"), width="stretch")
    st.caption(t("plan_gaps_note", lang))

    st.subheader(t("plan_list", lang))
    st.caption(t("plan_list_note", lang))
    table = pd.DataFrame({
        t("site", lang): plan["siteCode"],
        t("site_name", lang): plan["name"],
        t("city", lang): plan["city_name"],
        t("col_tests", lang): plan["n_reasons"],
        t("col_reasons", lang): plan["reasons"],
        comp_name(A, lang): plan[A].round(2),
        comp_name("composite_obs", lang): plan["composite"].round(2),
        t("col_sampled", lang): plan["samplingDate"].astype(str).str[:10],
    })
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button(t("download_plan", lang), table.to_csv(index=False).encode("utf-8"),
                       file_name="aquasentinel_campaign_plan.csv", mime="text/csv")



# ------------------------------------------------------------------ Contamination profiles
def page_fingerprints():
    st.title(t("fp_title", lang))
    st.markdown(t("fp_intro", lang))
    ins_list, lab, profiles = discover()
    fp = next(i for i in ins_list if i["id"] == "INS-FINGERPRINT")
    cols = st.columns(len(profiles))
    names = {}
    for col, (cid, p) in zip(cols, profiles.items()):
        names[cid] = f"{t('profile', lang)} {chr(65 + cid)}"
        with col, st.container(border=True):
            st.markdown(f"**{names[cid]}** — {p['label']}")
            st.caption(f"{p['n']} {t('sites_lc', lang)}")
            for comp in RISK_COMPONENTS:
                v = p["means"][comp]
                st.markdown(f"{comp_name(comp, lang)}  \n`{_bar(int(round(v * 4)))}` {v:.2f}")
            st.caption(t("eg", lang) + " " + ", ".join(p["examples"]))
            st.caption(", ".join(f"{k} {v}" for k, v in p["cities"].items()))

    plot = lab[["siteCode", "city_name", "cluster"] + RISK_COMPONENTS].copy()
    plot["profile"] = plot["cluster"].map(names)
    order = [names[c] for c in sorted(names)]
    color = alt.Color("profile:N", title=None, sort=order,
                      scale=alt.Scale(domain=order, range=PROFILE_COLORS[:len(order)]),
                      legend=alt.Legend(orient="top"))
    shape = alt.Shape("profile:N", sort=order, legend=None)   # never colour alone

    def chart(x, y, title):
        return (alt.Chart(plot, title=alt.Title(title, anchor="start", fontSize=14))
                .mark_point(size=70, filled=True, opacity=0.8, stroke="white", strokeWidth=1)
                .encode(x=alt.X(f"{x}:Q", title=comp_name(x, lang), scale=alt.Scale(domain=[0, 1])),
                        y=alt.Y(f"{y}:Q", title=comp_name(y, lang), scale=alt.Scale(domain=[0, 1])),
                        color=color, shape=shape,
                        tooltip=[alt.Tooltip("siteCode:N", title=t("site", lang)),
                                 alt.Tooltip("city_name:N", title=t("city", lang)),
                                 alt.Tooltip("profile:N", title=t("profile", lang)),
                                 alt.Tooltip(f"{x}:Q", title=comp_name(x, lang), format=".2f"),
                                 alt.Tooltip(f"{y}:Q", title=comp_name(y, lang), format=".2f")])
                .properties(height=320)
                .configure_axis(gridColor="#e9eceb", domainColor="#c9cfcd", tickColor="#c9cfcd"))

    c = st.columns(2)
    c[0].altair_chart(chart(F, P, t("fp_chart_sep", lang)), width="stretch")
    c[1].altair_chart(chart(F, A, t("fp_chart_arg", lang)), width="stretch")
    st.caption(f"**{t('challenge_lbl', lang)}:** {fp['challenge']['detail']}")


# ------------------------------------------------------------------ Map
def page_map():
    import folium
    from streamlit_folium import st_folium

    st.title(t("map_title", lang))
    c = st.columns([2, 1, 1])
    layers = ["composite_obs"] + RISK_COMPONENTS + ["nitrate_mgL"]
    layer = c[0].selectbox(t("layer", lang), layers, index=layers.index(A),
                           format_func=lambda k: comp_name(k, lang))
    cities = sorted(df["city_name"].unique())
    city = c[1].selectbox(t("zoom_to", lang), [t("all_cities", lang)] + cities)
    show_citizen = c[2].checkbox(t("show_citizen", lang), False)

    dd = df.dropna(subset=[layer, "latitude", "longitude"]).copy()
    focus = dd if city == t("all_cities", lang) else dd[dd["city_name"] == city]
    m = folium.Map(location=[focus["latitude"].mean(), focus["longitude"].mean()],
                   zoom_start=4 if city == t("all_cities", lang) else 11, tiles="OpenStreetMap")
    vmax = dd[layer].quantile(0.98) if layer == "nitrate_mgL" else 1.0
    for _, r in dd.iterrows():
        v = r[layer]
        folium.CircleMarker(
            [r["latitude"], r["longitude"]], radius=7, color="#ffffff", weight=1.5,
            fill=True, fill_color=risk_color(v / vmax), fill_opacity=0.95,
            tooltip=f"{r['siteCode']} · {comp_name(layer, lang)} {v:.2f}",
            popup=folium.Popup(
                f"<b>{r['siteCode']} — {r['name']}</b><br>{r['city_name']}<br>"
                + "<br>".join(f"{comp_name(k, lang)}: {r[k]:.2f}"
                              for k in ["composite_obs"] + RISK_COMPONENTS if pd.notna(r[k])),
                max_width=260),
        ).add_to(m)
    if show_citizen:
        for _, r in quality.cleaned_registry(citizen_quality()).iterrows():
            folium.CircleMarker(
                [r["latitude"], r["longitude"]], radius=5, color="#52514e", weight=2,
                fill=False, tooltip=f"{t('citizen_site', lang)}: {r['name']}").add_to(m)
    st_folium(m, use_container_width=True, height=540, returned_objects=[])

    unit = "" if layer != "nitrate_mgL" else f" (× {vmax:.1f} mg/L)"
    edges = [0] + BANDS + [1]
    swatches = "".join(
        f"<span style='display:inline-block;width:14px;height:14px;border-radius:3px;"
        f"background:{col};margin:0 6px 0 14px;vertical-align:-2px'></span>"
        f"{edges[i]:.2f}–{edges[i + 1]:.2f}" for i, col in enumerate(RAMP))
    st.markdown(f"<div style='font-size:0.85rem'>{comp_name(layer, lang)}{unit}:{swatches}</div>",
                unsafe_allow_html=True)
    st.caption(t("map_caption", lang).format(n=len(dd), total=len(df)))


# ------------------------------------------------------------------ Health card
def _value_tiles(cols, row):
    """Four stat tiles: composite + the three components, each with its band in words."""
    for col, c_ in zip(cols, ["composite_obs"] + RISK_COMPONENTS):
        col.metric(comp_name(c_, lang), f"{row[c_]:.2f}")
        col.caption(risk_band(row[c_], lang))


def page_health_card():
    st.title(t("card_title", lang))
    codes = labelled["siteCode"].tolist()
    code = st.selectbox(t("select_site", lang), codes,
                        index=codes.index("T10") if "T10" in codes else 0)
    row = df[df["siteCode"] == code].iloc[0]

    st.subheader(f"{row['siteCode']} — {row['name']} · {row['city_name']}")
    st.caption(t("sampled_on", lang).format(d=str(row["samplingDate"])[:10]))
    cols = st.columns(4)
    comp = row["composite_obs"]
    _value_tiles(cols, row)

    # Where the composite misleads: say which dimension is highest and how it ranks.
    top_c = max(RISK_COMPONENTS, key=lambda c_: row[c_])
    pct_dim = (labelled[top_c] < row[top_c]).mean() * 100
    pct_comp = (labelled["composite_obs"] < comp).mean() * 100
    if pct_dim - pct_comp >= 25:
        st.warning(t("card_hidden", lang).format(
            dim=comp_name(top_c, lang), pd=f"{pct_dim:.0f}", pc=f"{pct_comp:.0f}"))
    city_sites = labelled[labelled["city_name"] == row["city_name"]]
    st.write(t("percentile_line", lang).format(
        city=row["city_name"], pc=f"{(city_sites['composite_obs'] < comp).mean() * 100:.0f}",
        pe=f"{pct_comp:.0f}"))
    if pd.notna(row.get("nitrate_mgL")):
        st.write(t("nitrate_line", lang).format(v=f"{row['nitrate_mgL']:.2f}", ref=NITRATE_REF))

    with st.expander(t("card_context", lang)):
        st.caption(t("card_context_note", lang))
        model = load_model()
        if model is not None:
            x = feat_df[feat_df["siteCode"] == code][feat_names].to_numpy(float)[0]
            drivers = explain.top_drivers_text(model, x, "composite", k=3)
            for d_ in drivers or [t("no_drivers", lang)]:
                st.markdown(f"- {d_}")
    st.info(t("card_honesty", lang))


# ------------------------------------------------------------------ Landscape & model
def page_drivers():
    st.title(t("drivers_title", lang))
    st.markdown(t("drivers_intro", lang))
    cv = load_cv()
    if cv:
        rows = []
        for tgt, r in cv.items():
            mc = r["loco"].get("mean_city_spearman")
            rows.append({
                t("col_target", lang): comp_name(tgt if tgt != "composite" else "composite_obs", lang),
                t("col_model_err", lang): round(r["loco"]["mae"], 3),
                t("col_base_err", lang): round(r["loco_baseline"]["mae"], 3),
                t("col_beats", lang): t("yes", lang) if r["loco"]["mae"] < r["loco_baseline"]["mae"]
                else t("no", lang),
                t("col_city_rank", lang): "—" if mc is None else f"{mc:+.2f}",
            })
        st.subheader(t("validation", lang))
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.caption(t("validation_note", lang))
    st.error(t("model_honesty", lang))

    st.subheader(t("associations", lang))
    st.caption(t("associations_note", lang))
    sig_path = ROOT / "outputs" / "spearman_signals.csv"
    if sig_path.exists():
        sig = pd.read_csv(sig_path).head(12)
        sig["sign"] = np.where(sig["rho"] >= 0, t("positive", lang), t("negative", lang))
        chart = (
            alt.Chart(sig)
            .mark_bar(color=SERIES, cornerRadiusEnd=4, height=14)
            .encode(x=alt.X("rho:Q", title="Spearman rho", scale=alt.Scale(domain=[-0.4, 0.4])),
                    y=alt.Y("plain:N", sort=None, title=None,
                            axis=alt.Axis(labelLimit=320)),
                    tooltip=[alt.Tooltip("plain:N", title=t("feature", lang)),
                             alt.Tooltip("rho:Q", format="+.2f"),
                             alt.Tooltip("p:Q", title=f"p ({t('uncorrected', lang)})", format=".3f"),
                             alt.Tooltip("n:Q")])
            .properties(height=28 * len(sig) + 30)
            .configure_axis(gridColor="#e9eceb", domainColor="#c9cfcd", tickColor="#c9cfcd"))
        st.altair_chart(chart, width="stretch")


# ------------------------------------------------------------------ Citizen site check
def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((p2 - p1) / 2) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


def page_citizen():
    st.title(t("citizen_title", lang))
    st.markdown(t("citizen_intro", lang))
    with st.form("citizen"):
        c = st.columns(3)
        name = c[0].text_input(t("site_name", lang), "Zwalm")
        lat = c[1].number_input(t("latitude", lang), value=3.71, format="%.5f")
        lon = c[2].number_input(t("longitude", lang), value=50.88, format="%.5f")
        go = st.form_submit_button(t("check_btn", lang), type="primary")
    if not go:
        st.caption(t("citizen_try", lang))
        return

    res = quality.assess_new_submission(name, lat, lon, data.load_user_generated(),
                                        data.research_points())
    flags = res["flags"]

    st.subheader(t("step1", lang))
    if "INVALID_COORDS" in flags:
        st.error(t("f_invalid", lang))
        return
    plat, plon = lat, lon
    if "LIKELY_SWAPPED" in flags:
        plat, plon = res["suggestion"]["swapped_latlon"]
        st.warning(t("f_swapped", lang).format(lat=plat, lon=plon))
    if "JUNK_NAME" in flags:
        st.warning(t("f_junk", lang))
    if res["duplicate_of"]:
        d = res["duplicate_of"]
        st.warning(t("f_duplicate", lang).format(name=d["name"], m=d["distance_m"]))
    if not flags:
        st.success(t("f_ok", lang))

    st.subheader(t("step2", lang))
    sites = df.dropna(subset=["latitude", "longitude"])
    km = _haversine_km(plat, plon, sites["latitude"].to_numpy(), sites["longitude"].to_numpy())
    near = sites.iloc[int(np.argmin(km))]
    near_km = float(km.min())
    if near_km <= NEAR_SITE_KM:
        st.write(t("near_site", lang).format(code=near["siteCode"], name=near["name"],
                                             city=near["city_name"], km=f"{near_km:.1f}"))
        if pd.notna(near["composite_obs"]):
            cols = st.columns(4)
            _value_tiles(cols, near)
            st.caption(t("near_caveat", lang).format(d=str(near["samplingDate"])[:10]))
        else:
            st.caption(t("near_nolab", lang))
    elif not res["outside_coverage"]:
        st.info(t("in_city", lang).format(city=near["city_name"], km=f"{near_km:.1f}"))
    else:
        st.info(t("new_coverage", lang).format(km=f"{near_km:,.0f}"))

    st.subheader(t("step3", lang))
    actions = []
    if "LIKELY_SWAPPED" in flags:
        actions.append(t("a_fix_coords", lang))
    if res["duplicate_of"]:
        actions.append(t("a_add_visit", lang).format(name=res["duplicate_of"]["name"]))
    if "JUNK_NAME" in flags:
        actions.append(t("a_rename", lang))
    if near_km <= NEAR_SITE_KM and pd.notna(near["composite_obs"]) \
            and max(near[c_] for c_ in RISK_COMPONENTS) >= BANDS[2]:
        actions.append(t("a_avoid", lang))
    actions += [t("a_photo", lang), t("a_report", lang)]
    for a in actions:
        st.markdown(f"- {a}")
    st.caption(t("citizen_guardrail", lang))


# ------------------------------------------------------------------ Data quality
def page_quality():
    st.title(t("quality_title", lang))
    st.markdown(t("quality_intro", lang))
    res = citizen_quality()
    s = res.summary
    clean = quality.cleaned_registry(res)
    cols = st.columns(6)
    cols[0].metric(t("q_total", lang), s["n_total"])
    cols[1].metric(t("q_review", lang), s["n_review"])
    cols[2].metric(t("q_junk", lang), s["junk_name"])
    cols[3].metric(t("q_swapped", lang), s["likely_swapped"])
    cols[4].metric(t("q_dup", lang), s["duplicate"],
                   help=t("q_dup_help", lang).format(n=s["duplicate_clusters"]))
    cols[5].metric(t("q_clean", lang), len(clean), help=t("q_clean_help", lang))
    st.caption(t("q_outside", lang).format(n=int((~clean["in_lab_coverage"]).sum()),
                                           total=len(clean)))

    only = st.checkbox(t("show_flagged", lang), True)
    view = res.df[res.df["status"] == "REVIEW"] if only else res.df

    def fix(r):
        out = []
        sug = r["suggestion"]
        if "swapped_latlon" in sug:
            out.append(t("fix_swap", lang).format(lat=sug["swapped_latlon"][0],
                                                  lon=sug["swapped_latlon"][1]))
        if "merge_into" in sug:
            out.append(t("fix_merge", lang).format(name=sug["merge_into"], n=sug["cluster_size"]))
        if "JUNK_NAME" in r["flags"]:
            out.append(t("fix_junk", lang))
        return "; ".join(out)

    table = pd.DataFrame({
        "ID": view["userSiteCode"], t("site_name", lang): view["name"],
        t("latitude", lang): view["latitude"], t("longitude", lang): view["longitude"],
        t("col_flags", lang): view["flags"],
        t("col_fix", lang): [fix(r) for _, r in view.iterrows()],
        t("col_notes", lang): view["notes"],
    })
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button(t("download_clean", lang).format(n=len(clean)),
                       clean.to_csv(index=False).encode("utf-8"),
                       file_name="citizen_sites_cleaned.csv", mime="text/csv")
    with st.expander(t("rules_title", lang)):
        st.markdown(t("rules_body", lang).format(
            dup=int(quality.DUP_RADIUS_M), cov=int(quality.COVERAGE_KM),
            far=int(quality.SWAP_FAR_KM), near=int(quality.SWAP_NEAR_KM)))


# ------------------------------------------------------------------ About
def page_about():
    st.title(t("about_title", lang))
    st.markdown(t("about_body", lang))
    st.info(t("honesty_banner", lang))
    dd = ROOT / "docs" / "data_dictionary.md"
    if dd.exists():
        with st.expander(t("data_dictionary", lang)):
            st.markdown(dd.read_text())
    ins_list, _, _ = discover()
    st.download_button(t("download_insights", lang),
                       json.dumps({"counts": insights.counts(ins_list), "insights": ins_list},
                                  indent=2).encode("utf-8"),
                       file_name="aquasentinel_insights.json", mime="application/json")


PAGES = {
    "insight_feed": page_insight_feed, "watchlist": page_watchlist, "plan": page_plan,
    "fingerprints": page_fingerprints, "map": page_map,
    "health_card": page_health_card, "citizen": page_citizen,
    "quality": page_quality, "drivers": page_drivers, "about": page_about,
}
PAGES[section]()

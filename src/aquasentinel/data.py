"""Data loading and joining.

Single source of truth for reading the eight raw CSVs and assembling the
analysis table. Everything downstream (quality, features, model, app) imports
from here so the join logic lives in exactly one place.
"""
from __future__ import annotations

from pathlib import Path
import functools

import pandas as pd

# Resolve the raw-data directory relative to the repo root, so the package works
# whether it is run from a notebook, the app, or the CLI scripts.
_PKG_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = _PKG_ROOT / "data" / "raw"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / name)


def load_cities() -> pd.DataFrame:
    return _read("cities.csv")


def load_sites() -> pd.DataFrame:
    """Research sites with coordinates and city membership."""
    df = _read("sites.csv")
    # polygon columns arrive empty from the API export; drop to avoid confusion.
    return df.drop(columns=[c for c in df.columns if c.startswith("polygon")], errors="ignore")


def load_health_risks() -> pd.DataFrame:
    return _read("health_risks.csv")


def load_health_timeseries() -> pd.DataFrame:
    return _read("health_timeseries.csv")


def load_nitrates() -> pd.DataFrame:
    """One nitrate value per site. Reduce to a single row per site (mean, guarded)."""
    df = _read("nitrates.csv")
    agg = (
        df.groupby("siteCode", as_index=False)["statusOfNitrate"]
        .mean()
        .rename(columns={"statusOfNitrate": "nitrate_mgL"})
    )
    return agg


def load_urban_parameters() -> pd.DataFrame:
    df = _read("urban_parameters.csv")
    return df.drop(columns=["id", "samplingDate"], errors="ignore")


def load_weather_summary() -> pd.DataFrame:
    return _read("weather_summary.csv")


def load_user_generated() -> pd.DataFrame:
    return _read("user_generated_sites.csv")


def research_points() -> list[tuple[float, float]]:
    """(lat, lon) of every lab-monitored research site — the reference set the
    citizen-data validator uses for swap detection and lab coverage."""
    s = load_sites()[["latitude", "longitude"]].dropna()
    return list(map(tuple, s.to_numpy(float)))


@functools.lru_cache(maxsize=1)
def build_analysis_table() -> pd.DataFrame:
    """Left-join every research-site source onto the site master table.

    Keyed on the research-site code (``code`` in sites, ``researchSiteCode`` /
    ``siteCode`` elsewhere). Returns one row per site with risk targets, nitrate,
    landscape features and climate context. Missing joins stay as NaN so the
    coverage table and the modelling step can handle them explicitly.
    """
    sites = load_sites().rename(columns={"code": "siteCode"})
    risks = load_health_risks().rename(columns={"researchSiteCode": "siteCode"})
    risks = risks.drop(columns=["id"], errors="ignore")
    urban = load_urban_parameters().rename(columns={"researchSiteCode": "siteCode"})
    nitr = load_nitrates()
    wx = load_weather_summary()

    df = sites.merge(risks, on="siteCode", how="left")
    df = df.merge(nitr, on="siteCode", how="left")
    df = df.merge(urban, on="siteCode", how="left")
    df = df.merge(wx, on="siteCode", how="left")
    return df


def coverage_table() -> pd.DataFrame:
    """Which sites appear in which source file — the join-coverage report."""
    sites = set(load_sites()["code"])
    sources = {
        "sites": sites,
        "health_risks": set(load_health_risks()["researchSiteCode"]),
        "nitrates": set(load_nitrates()["siteCode"]),
        "urban_parameters": set(load_urban_parameters()["researchSiteCode"]),
        "weather_summary": set(load_weather_summary()["siteCode"]),
        "health_timeseries": set(load_health_timeseries()["siteCode"]),
    }
    all_codes = set().union(*sources.values())
    rows = []
    for code in sorted(all_codes):
        row = {"siteCode": code}
        for name, codes in sources.items():
            row[name] = code in codes
        rows.append(row)
    return pd.DataFrame(rows)

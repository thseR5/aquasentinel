"""Feature engineering for the risk model.

Design choices tied to scientific honesty on n<=96:
  - Distances are log-transformed (heavy right skew; effect is multiplicative).
  - Landscape buffers span 8 radii per family and are highly collinear; we keep
    them all and lean on elastic-net's L2 grouping to share weight across a
    correlated family rather than hand-picking a radius (which would leak).
  - Every feature carries a plain-language label for the site health card.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Distance features: log1p transform (metres, right-skewed).
DISTANCE_FEATURES = [
    "distChampCulture", "distanceToHospitals", "distanceToLivingStreetRoad",
    "distanceToMotorwayRoad", "distanceToSewageStations",
]

RADII = [50, 100, 250, 500, 750, 1000, 1500, 2000]
BUFFER_FAMILIES = {
    "impervious": "imperviousPct{r}m",
    "urban": "urbanPct{r}m",
    "vegCover": "vegCoverFrac{r}m",
    "patchDensityVeg": "patchDensityVeg{r}m",
    "patchDensity": "patchDensity{r}m",
    "humanDensityProxy": "humanDensityProxy{r}m",
}

WEATHER_FEATURES = ["meanTemperatureC", "maxTemperatureC", "meanPrecipitationMm", "maxPrecipitationMm"]
OTHER_FEATURES = ["nitrate_mgL", "altitude"]

# Human-readable labels for the health card's "top drivers in plain words".
PLAIN_LABELS = {
    "log_distChampCulture": "distance to crop fields",
    "log_distanceToHospitals": "distance to hospitals",
    "log_distanceToLivingStreetRoad": "distance to residential streets",
    "log_distanceToMotorwayRoad": "distance to motorways",
    "log_distanceToSewageStations": "distance to wastewater stations",
    "nitrate_mgL": "nitrate concentration",
    "altitude": "site altitude",
    "meanTemperatureC": "mean temperature", "maxTemperatureC": "peak temperature",
    "meanPrecipitationMm": "mean rainfall", "maxPrecipitationMm": "peak rainfall",
}
for fam, tmpl in BUFFER_FAMILIES.items():
    human = {
        "impervious": "paved/impervious surface", "urban": "urban land cover",
        "vegCover": "vegetation cover", "patchDensityVeg": "vegetation fragmentation",
        "patchDensity": "landscape fragmentation", "humanDensityProxy": "human density",
    }[fam]
    for r in RADII:
        PLAIN_LABELS[tmpl.format(r=r)] = f"{human} within {r} m"


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (feature_frame, feature_names). Adds log-distance columns."""
    X = df.copy()
    log_cols = []
    for c in DISTANCE_FEATURES:
        if c in X.columns:
            lc = f"log_{c}"
            X[lc] = np.log1p(X[c].clip(lower=0))
            log_cols.append(lc)

    buffer_cols = [tmpl.format(r=r) for tmpl in BUFFER_FAMILIES.values() for r in RADII]
    feature_names = (
        log_cols
        + [c for c in buffer_cols if c in X.columns]
        + [c for c in WEATHER_FEATURES if c in X.columns]
        + [c for c in OTHER_FEATURES if c in X.columns]
    )
    return X[["siteCode", "city_name"] + feature_names], feature_names


def plain(feature: str) -> str:
    return PLAIN_LABELS.get(feature, feature)

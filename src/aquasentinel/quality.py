"""Citizen-data quality validation.

Directly answers the hackathon's "AI-Supported Assessment: citizen observations
are inconsistent and error-prone" problem. Every rule is deterministic and
explainable — no black box — so a city officer can trust the triage.

Flags produced per submission:
  - INVALID_COORDS   : latitude/longitude outside valid ranges
  - LIKELY_SWAPPED    : looks like lat/long were entered in the wrong fields
  - JUNK_NAME         : test / placeholder / gibberish names
  - DUPLICATE         : within DUP_RADIUS_M of another submission
  - OUT_OF_REGION     : not inside any partner-country bounding box (info, not error)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import pandas as pd

DUP_RADIUS_M = 25.0

# Coarse bounding boxes for the five partner countries (lat_min, lat_max, lon_min, lon_max).
PARTNER_BBOXES = {
    "Portugal": (36.8, 42.2, -9.6, -6.1),
    "France": (41.3, 51.1, -5.2, 9.6),
    "Belgium": (49.4, 51.6, 2.5, 6.5),
    "Italy": (36.6, 47.1, 6.6, 18.6),
    "Norway": (57.9, 71.4, 4.5, 31.2),
}

# Names that signal a test / placeholder rather than a real stream site.
_JUNK_EXACT = {"test", "test1", "test123", "random", "this site", "x1", "x", "aaa", "asdf"}
_JUNK_SUBSTR = ("test", "random")


def _is_junk_name(name: str) -> bool:
    if not isinstance(name, str) or not name.strip():
        return True
    n = name.strip().lower()
    if n in _JUNK_EXACT:
        return True
    if any(sub in n for sub in _JUNK_SUBSTR):
        return True
    # No vowels and short -> likely keyboard mash ("fgdgh", "dfgh").
    if len(n) <= 6 and not re.search(r"[aeiou]", n):
        return True
    return False


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _in_any_partner_bbox(lat, lon) -> bool:
    for (la0, la1, lo0, lo1) in PARTNER_BBOXES.values():
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return True
    return False


@dataclass
class QualityResult:
    df: pd.DataFrame                       # original rows + flag columns
    summary: dict = field(default_factory=dict)


def validate_coordinates(lat, lon) -> tuple[list[str], dict]:
    """Validate a single coordinate pair. Returns (flags, suggestions)."""
    flags: list[str] = []
    suggest: dict = {}
    if lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)):
        return ["INVALID_COORDS"], suggest

    valid_lat = -90 <= lat <= 90
    valid_lon = -180 <= lon <= 180
    if not (valid_lat and valid_lon):
        flags.append("INVALID_COORDS")

    # Swap heuristic: current pair not in a partner box, but the swapped pair is,
    # OR latitude magnitude is small while longitude magnitude is large in a way
    # that only makes sense reversed (e.g. lat=3.71, lon=50.88 in Belgium).
    if valid_lat and valid_lon and not _in_any_partner_bbox(lat, lon):
        if -90 <= lon <= 90 and _in_any_partner_bbox(lon, lat):
            flags.append("LIKELY_SWAPPED")
            suggest["swapped_latlon"] = (round(lon, 6), round(lat, 6))
    return flags, suggest


def validate_submissions(df: pd.DataFrame,
                         lat_col: str = "latitude",
                         lon_col: str = "longitude",
                         name_col: str = "name") -> QualityResult:
    """Run every rule over a table of citizen submissions."""
    out = df.copy().reset_index(drop=True)
    flags_col: list[list[str]] = [[] for _ in range(len(out))]
    suggestions: list[dict] = [{} for _ in range(len(out))]

    for i, row in out.iterrows():
        lat, lon = row.get(lat_col), row.get(lon_col)
        cf, cs = validate_coordinates(lat, lon)
        flags_col[i].extend(cf)
        suggestions[i].update(cs)

        if _is_junk_name(row.get(name_col)):
            flags_col[i].append("JUNK_NAME")

        # Out-of-region is informational: citizen science is global, but these
        # points cannot be joined to the partner landscape/health datasets.
        try:
            if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
                if "LIKELY_SWAPPED" not in flags_col[i] and not _in_any_partner_bbox(lat, lon):
                    flags_col[i].append("OUT_OF_REGION")
        except TypeError:
            pass

    # Duplicate detection: O(n^2) is fine at citizen-submission scale (<10k).
    for i in range(len(out)):
        if "INVALID_COORDS" in flags_col[i]:
            continue
        for j in range(i + 1, len(out)):
            if "INVALID_COORDS" in flags_col[j]:
                continue
            try:
                d = _haversine_m(out.at[i, lat_col], out.at[i, lon_col],
                                 out.at[j, lat_col], out.at[j, lon_col])
            except (TypeError, ValueError):
                continue
            if d <= DUP_RADIUS_M:
                if "DUPLICATE" not in flags_col[i]:
                    flags_col[i].append("DUPLICATE")
                if "DUPLICATE" not in flags_col[j]:
                    flags_col[j].append("DUPLICATE")

    out["flags"] = ["|".join(f) if f else "OK" for f in flags_col]
    out["n_flags"] = [len(f) for f in flags_col]
    out["suggestion"] = suggestions
    out["status"] = ["OK" if not f else "REVIEW" for f in flags_col]

    summary = {
        "n_total": int(len(out)),
        "n_ok": int((out["status"] == "OK").sum()),
        "n_review": int((out["status"] == "REVIEW").sum()),
        "junk_name": int(sum("JUNK_NAME" in f for f in flags_col)),
        "likely_swapped": int(sum("LIKELY_SWAPPED" in f for f in flags_col)),
        "invalid_coords": int(sum("INVALID_COORDS" in f for f in flags_col)),
        "duplicate": int(sum("DUPLICATE" in f for f in flags_col)),
        "out_of_region": int(sum("OUT_OF_REGION" in f for f in flags_col)),
    }
    return QualityResult(df=out, summary=summary)

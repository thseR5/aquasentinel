"""Citizen-data quality validation.

Answers the hackathon's "citizen observations are inconsistent and error-prone"
problem with rules that are deterministic and explainable — no black box — so a
researcher or city officer can see exactly why an entry was flagged.

FLAGS (the entry needs fixing; status = REVIEW)
  INVALID_COORDS   latitude/longitude outside valid ranges
  LIKELY_SWAPPED   latitude and longitude entered in the wrong fields
  JUNK_NAME        test / placeholder / keyboard-mash names
  DUPLICATE        within DUP_RADIUS_M of another registration (same place)

NOTES (information only; the entry stays OK)
  OUTSIDE_COVERAGE valid site, but farther than COVERAGE_KM from any lab-monitored
                   site, so it cannot be compared with lab data. Citizen science is
                   global — these sites are welcome, not errors.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

DUP_RADIUS_M = 25.0      # two registrations this close are the same place
COVERAGE_KM = 50.0       # farther than this from any monitored site = outside coverage
SWAP_FAR_KM = 300.0      # "nowhere near anything we know"
SWAP_NEAR_KM = 50.0      # "right next to something we know"

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


def _is_junk_name(name) -> bool:
    if not isinstance(name, str) or not name.strip():
        return True
    n = name.strip().lower()
    if n in _JUNK_EXACT or any(sub in n for sub in _JUNK_SUBSTR):
        return True
    # Short and vowel-free -> keyboard mash ("fgdgh").
    return len(n) <= 6 and not re.search(r"[aeiou]", n)


def _haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres. lat2/lon2 may be numpy arrays."""
    r = 6371000.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((p2 - p1) / 2) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * np.arcsin(np.sqrt(a))


def _in_any_partner_bbox(lat, lon) -> bool:
    return any(la0 <= lat <= la1 and lo0 <= lon <= lo1
               for (la0, la1, lo0, lo1) in PARTNER_BBOXES.values())


def _valid(lat, lon) -> bool:
    try:
        return (not math.isnan(lat) and not math.isnan(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180)
    except TypeError:
        return False


def _nearest_km(lat, lon, anchors: np.ndarray) -> float:
    if anchors is None or len(anchors) == 0:
        return float("inf")
    return float(np.min(_haversine_m(lat, lon, anchors[:, 0], anchors[:, 1])) / 1000.0)


def validate_coordinates(lat, lon, anchors: np.ndarray | None = None) -> tuple[list[str], dict]:
    """Validate one coordinate pair. `anchors` is an (n, 2) array of known points
    (monitored sites, other registrations) used to recognise a swap anywhere in
    the world. Returns (flags, suggestions)."""
    if not _valid(lat, lon):
        return ["INVALID_COORDS"], {}
    flags, suggest = [], {}
    if -90 <= lon <= 90:  # the swapped pair must itself be a valid coordinate
        # Rule A: wrong side of the world for a partner country, right side when swapped.
        swap_a = not _in_any_partner_bbox(lat, lon) and _in_any_partner_bbox(lon, lat)
        # Rule B: nowhere near any known point, but right next to one when swapped.
        swap_b = (anchors is not None and len(anchors) > 0
                  and _nearest_km(lat, lon, anchors) > SWAP_FAR_KM
                  and _nearest_km(lon, lat, anchors) <= SWAP_NEAR_KM)
        if swap_a or swap_b:
            flags.append("LIKELY_SWAPPED")
            suggest["swapped_latlon"] = (round(float(lon), 6), round(float(lat), 6))
    return flags, suggest


@dataclass
class QualityResult:
    df: pd.DataFrame                       # original rows + flag columns
    summary: dict = field(default_factory=dict)


def _as_anchor_array(reference) -> np.ndarray:
    if reference is None:
        return np.empty((0, 2))
    arr = np.asarray(reference, dtype=float).reshape(-1, 2)
    return arr[~np.isnan(arr).any(axis=1)]


def validate_submissions(df: pd.DataFrame,
                         lat_col: str = "latitude",
                         lon_col: str = "longitude",
                         name_col: str = "name",
                         reference=None) -> QualityResult:
    """Run every rule over a table of citizen site registrations.

    `reference`: optional list/array of (lat, lon) for lab-monitored sites. It
    sharpens swap detection and defines lab coverage. Without it, coverage falls
    back to the partner-country boxes.
    """
    out = df.copy().reset_index(drop=True)
    n = len(out)
    lats = pd.to_numeric(out[lat_col], errors="coerce").to_numpy(float)
    lons = pd.to_numeric(out[lon_col], errors="coerce").to_numpy(float)
    ref = _as_anchor_array(reference)
    ok = np.array([_valid(lats[i], lons[i]) for i in range(n)])

    # Pairwise distances between valid registrations (fine at citizen scale, <10k).
    dist = np.full((n, n), np.inf)
    for i in np.flatnonzero(ok):
        dist[i, ok] = _haversine_m(lats[i], lons[i], lats[ok], lons[ok])
        dist[i, i] = np.inf

    # Duplicate clusters: connected groups of registrations within DUP_RADIUS_M.
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in zip(*np.nonzero(dist <= DUP_RADIUS_M)):
        parent[find(int(i))] = find(int(j))
    roots = [find(i) for i in range(n)]
    sizes = pd.Series(roots).value_counts()
    cluster_no = {r: k + 1 for k, r in enumerate(sorted(r for r in sizes.index if sizes[r] > 1))}

    flags_col: list[list[str]] = [[] for _ in range(n)]
    notes_col: list[list[str]] = [[] for _ in range(n)]
    suggestions: list[dict] = [{} for _ in range(n)]
    clusters: list = [None] * n

    # A registration can vouch for a neighbour only if it is itself "supported":
    # near a monitored site, or near another distinct registration. A lone point
    # (possibly a swap that landed in the ocean) vouches for nothing — otherwise a
    # bad entry could make a good neighbour look swapped.
    roots_arr = np.array(roots)
    near_m = SWAP_NEAR_KM * 1000.0
    supported = np.zeros(n, dtype=bool)
    for i in np.flatnonzero(ok):
        other_cluster = ok & (roots_arr != roots[i])
        supported[i] = (_nearest_km(lats[i], lons[i], ref) <= SWAP_NEAR_KM
                        or bool((dist[i, other_cluster] <= near_m).any()))

    for i in range(n):
        lat, lon = lats[i], lons[i]
        # Anchors for the swap test: monitored sites + every OTHER supported
        # registration (a point's own duplicates are excluded, or two identical
        # swapped entries would vouch for each other).
        others = supported & (roots_arr != roots[i])
        others[i] = False
        anchors = np.vstack([ref, np.column_stack([lats[others], lons[others]])])
        cf, cs = validate_coordinates(lat, lon, anchors)
        flags_col[i].extend(cf)
        suggestions[i].update(cs)

        if _is_junk_name(out.at[i, name_col] if name_col in out.columns else None):
            flags_col[i].append("JUNK_NAME")

        if roots[i] in cluster_no:
            flags_col[i].append("DUPLICATE")
            clusters[i] = cluster_no[roots[i]]
            first = min(j for j in range(n) if roots[j] == roots[i])
            suggestions[i]["merge_into"] = str(out.at[first, name_col])
            suggestions[i]["cluster_size"] = int(sizes[roots[i]])

        if ok[i]:
            # Coverage is judged on the corrected position when a swap is suspected.
            clat, clon = suggestions[i].get("swapped_latlon", (lat, lon))
            outside = (_nearest_km(clat, clon, ref) > COVERAGE_KM if len(ref)
                       else not _in_any_partner_bbox(clat, clon))
            if outside:
                notes_col[i].append("OUTSIDE_COVERAGE")

    out["flags"] = ["|".join(f) if f else "OK" for f in flags_col]
    out["notes"] = ["|".join(f) for f in notes_col]
    out["n_flags"] = [len(f) for f in flags_col]
    out["cluster"] = clusters
    out["suggestion"] = suggestions
    out["status"] = ["OK" if not f else "REVIEW" for f in flags_col]

    has = lambda flag: int(sum(flag in f for f in flags_col))
    n_dup, n_clusters = has("DUPLICATE"), len(cluster_no)
    summary = {
        "n_total": int(n),
        "n_ok": int((out["status"] == "OK").sum()),
        "n_review": int((out["status"] == "REVIEW").sum()),
        "junk_name": has("JUNK_NAME"),
        "likely_swapped": has("LIKELY_SWAPPED"),
        "invalid_coords": has("INVALID_COORDS"),
        "duplicate": n_dup,
        "duplicate_clusters": int(n_clusters),
        "outside_coverage": int(sum("OUTSIDE_COVERAGE" in f for f in notes_col)),
    }
    return QualityResult(df=out, summary=summary)


def assess_new_submission(name: str, lat: float, lon: float,
                          existing: pd.DataFrame | None = None,
                          reference=None,
                          lat_col: str = "latitude", lon_col: str = "longitude",
                          name_col: str = "name") -> dict:
    """Check ONE new registration at the moment of entry.

    Returns flags, a suggested coordinate fix, the existing registration it would
    duplicate (if any) and whether it is inside lab coverage. This is the
    capture-time version of `validate_submissions`.
    """
    ref = _as_anchor_array(reference)
    ex = existing if existing is not None else pd.DataFrame(columns=[name_col, lat_col, lon_col])
    if len(ex):
        # Clean the existing registrations first, so a bad entry cannot vouch for a
        # new one: swapped rows are moved to their corrected position.
        checked = validate_submissions(ex, lat_col, lon_col, name_col, reference).df
        ex = checked.copy()
        for i, sug in enumerate(checked["suggestion"]):
            if "swapped_latlon" in sug:
                ex.at[i, lat_col], ex.at[i, lon_col] = sug["swapped_latlon"]
    ex_xy = _as_anchor_array(ex[[lat_col, lon_col]].to_numpy()) if len(ex) else np.empty((0, 2))
    flags, suggest = validate_coordinates(lat, lon, np.vstack([ref, ex_xy]))
    if _is_junk_name(name):
        flags.append("JUNK_NAME")

    result = {"flags": flags, "suggestion": suggest, "duplicate_of": None,
              "outside_coverage": None, "nearest_monitored_km": None}
    if "INVALID_COORDS" in flags:
        return result
    # Judge duplicates and coverage on the corrected position when a swap is suspected.
    plat, plon = suggest.get("swapped_latlon", (lat, lon))
    if len(ex):
        ex_valid = ex[[_valid(a, b) for a, b in zip(ex[lat_col], ex[lon_col])]]
        if len(ex_valid):
            d = _haversine_m(plat, plon, ex_valid[lat_col].to_numpy(float),
                             ex_valid[lon_col].to_numpy(float))
            j = int(np.argmin(d))
            if d[j] <= DUP_RADIUS_M:
                flags.append("DUPLICATE")
                result["duplicate_of"] = {"name": str(ex_valid.iloc[j][name_col]),
                                          "distance_m": round(float(d[j]), 1)}
    if len(ref):
        km = _nearest_km(plat, plon, ref)
        result["nearest_monitored_km"] = round(km, 2)
        result["outside_coverage"] = bool(km > COVERAGE_KM)
    return result


def cleaned_registry(result: QualityResult, lat_col: str = "latitude",
                     lon_col: str = "longitude") -> pd.DataFrame:
    """Apply the suggested fixes: correct swapped coordinates, drop test/placeholder
    and invalid entries, and merge each duplicate cluster into one site (keeping the
    first registration and counting how many were merged)."""
    d = result.df.copy()
    for i, sug in enumerate(d["suggestion"]):
        if "swapped_latlon" in sug:
            d.at[i, lat_col], d.at[i, lon_col] = sug["swapped_latlon"]
    d = d[~d["flags"].str.contains("JUNK_NAME|INVALID_COORDS")]
    d["registrations_merged"] = 1
    keep = []
    for cl, grp in d.groupby("cluster", dropna=True):
        d.loc[grp.index[0], "registrations_merged"] = len(grp)
        keep.extend(grp.index[1:])
    d = d.drop(index=keep)
    d["in_lab_coverage"] = ~d["notes"].str.contains("OUTSIDE_COVERAGE")
    cols = [c for c in d.columns if c not in ("flags", "notes", "n_flags", "cluster",
                                              "suggestion", "status")]
    return d[cols].reset_index(drop=True)

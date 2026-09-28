"""Reproducibly fetch the raw data from the OneAquaHealth Resilience Map public API.

Writes the eight CSVs into data/raw/. Only public, unauthenticated endpoints are
used. Run:  python scripts/fetch_data.py

Note: a browser User-Agent header is required (the API returns 403 to the default
Python UA). This is a public read-only API; no credentials are used.
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

BASE = "https://api.enora-oah.eu/api"
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

START, END = "2023-01-01T00:00:00Z", "2024-12-31T00:00:00Z"


def get(ep: str):
    req = urllib.request.Request(BASE + ep, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        nk = f"{p}{k}"
        if isinstance(v, dict):
            o.update(flat(v, nk + "_"))
        elif isinstance(v, list):
            o[nk] = json.dumps(v)
        else:
            o[nk] = v
    return o


def save(name, rows):
    rows = [flat(r) if isinstance(r, dict) else {"value": r} for r in rows]
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(RAW / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"  {name}: {len(rows)} rows, {len(keys)} cols")


def main():
    print("Fetching core tables...")
    save("cities.csv", get("/cities/all"))
    sites = get("/sites/all")
    save("sites.csv", sites)
    save("health_risks.csv", get("/resilience-map/health-risks"))
    save("urban_parameters.csv", get("/resilience-map/urban-parameters"))
    try:
        save("user_generated_sites.csv", get("/sites/user-generated"))
    except Exception as e:
        print("  user-generated:", e)

    codes = [s["code"] for s in sites]
    print(f"Fetching per-site health, nitrates, weather for {len(codes)} sites...")

    hrows, nrows, wrows = [], [], []
    for i, s in enumerate(codes, 1):
        try:
            d = get(f"/resilience-map/health/{s}")
            for metric, pts in d.get("series", {}).items():
                for pt in pts or []:
                    hrows.append({"siteCode": s, "metric": metric,
                                  "date": pt["samplingDate"][:10], "value": pt["value"]})
        except Exception:
            pass
        try:
            d = get(f"/resilience-map/health-indicators/nitrates/{s}")
            for pt in d.get("series", []) or []:
                nrows.append({"siteCode": s, "date": pt["date"], "statusOfNitrate": pt["statusOfNitrate"]})
        except Exception:
            pass
        row = {"siteCode": s}
        for kind, path in [("temperature", "temperature/summary"), ("precipitation", "precipitation/summary")]:
            try:
                d = get(f"/resilience-map/weather/{path}?siteCode={s}&start={START}&end={END}")
                for k, v in d.items():
                    if k not in ("siteCode", "startDate", "endDate"):
                        row[k] = v
            except Exception:
                pass
        if len(row) > 1:
            wrows.append(row)
        if i % 20 == 0:
            print(f"  ...{i}/{len(codes)}")

    save("health_timeseries.csv", hrows)
    save("nitrates.csv", nrows)
    save("weather_summary.csv", wrows)
    print("Done. Raw CSVs in", RAW)


if __name__ == "__main__":
    sys.exit(main())

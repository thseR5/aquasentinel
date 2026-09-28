"""AquaSentinel interoperability API (Digital Health Standards track).

Exposes the joined stream-health data in three standards-aligned shapes:
  - OGC SensorThings-shaped JSON  (/v1.1/Things, /v1.1/Observations)
  - GeoJSON FeatureCollection      (/geojson/sites)
  - HL7 FHIR Observation           (/fhir/Observation/{siteCode})

The FHIR mapping makes the One Health link explicit: an environmental risk
measurement is expressed in the same clinical-data grammar public-health systems
already consume. This is a demonstration mapping, not a certified FHIR server.

Run:  uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


def clean(obj):
    """Recursively replace NaN/Inf and numpy scalars with JSON-safe values."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    try:
        import numpy as np
        if isinstance(obj, np.generic):
            val = obj.item()
            return clean(val)
    except ImportError:
        pass
    return obj

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aquasentinel import data, RISK_COMPONENTS  # noqa: E402

app = FastAPI(
    title="AquaSentinel Interoperability API",
    version="0.1.0",
    description="OGC SensorThings- and HL7 FHIR-aligned access to urban stream health data.",
)

# Risk components -> observed-property metadata (units are unitless 0-1 scaled scores).
_OBS_PROPS = {
    "scaledPathogenRisk": ("Pathogen risk (scaled)", "Relative pathogen presence risk, 0-1"),
    "scaledFecalRisk": ("Faecal indicator risk (scaled)", "Relative faecal contamination risk, 0-1"),
    "scaledArgRisk": ("Antibiotic-resistance-gene risk (scaled)", "Relative ARG risk, 0-1"),
    "healthRiskScore": ("Composite health-risk score", "Mean of the three component risks, 0-1"),
}


def _df():
    return data.build_analysis_table()


@app.get("/")
def root():
    return {
        "service": "AquaSentinel Interoperability API",
        "standards": ["OGC SensorThings v1.1 (shaped)", "GeoJSON", "HL7 FHIR R4 Observation"],
        "endpoints": ["/v1.1/Things", "/v1.1/Observations", "/geojson/sites",
                      "/fhir/Observation/{siteCode}", "/data-dictionary"],
    }


@app.get("/v1.1/Things")
def things():
    """Each monitoring site as a SensorThings Thing with a Location."""
    df = _df()
    items = []
    for _, r in df.iterrows():
        items.append({
            "@iot.id": r["siteCode"],
            "name": r["name"],
            "description": f"Urban stream monitoring site in {r['city_name']}",
            "properties": {"city": r["city_name"], "altitude_m": _num(r.get("altitude"))},
            "Locations": [{
                "name": r["name"], "encodingType": "application/geo+json",
                "location": {"type": "Point",
                             "coordinates": [_num(r["longitude"]), _num(r["latitude"])]},
            }],
        })
    return clean({"value": items, "@iot.count": len(items)})


@app.get("/v1.1/Observations")
def observations(siteCode: str | None = None):
    """Risk measurements as SensorThings Observations."""
    df = _df()
    if siteCode:
        df = df[df["siteCode"] == siteCode]
        if df.empty:
            raise HTTPException(404, f"Unknown siteCode {siteCode}")
    out = []
    oid = 0
    for _, r in df.iterrows():
        date = r.get("samplingDate")
        for comp in list(RISK_COMPONENTS) + ["healthRiskScore"]:
            val = r.get(comp)
            if val is None or (isinstance(val, float) and val != val):
                continue
            oid += 1
            name, desc = _OBS_PROPS[comp]
            out.append({
                "@iot.id": oid,
                "phenomenonTime": (str(date)[:10] if date == date else None),
                "result": round(float(val), 4),
                "Datastream": {"name": name, "description": desc,
                               "unitOfMeasurement": {"name": "scaled index", "symbol": "0-1"}},
                "FeatureOfInterest": {"@iot.id": r["siteCode"], "name": r["name"]},
            })
    return clean({"value": out, "@iot.count": len(out)})


@app.get("/geojson/sites")
def geojson_sites():
    df = _df()
    feats = []
    for _, r in df.iterrows():
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [_num(r["longitude"]), _num(r["latitude"])]},
            "properties": {
                "siteCode": r["siteCode"], "name": r["name"], "city": r["city_name"],
                **{c: _num(r.get(c)) for c in list(RISK_COMPONENTS) + ["healthRiskScore", "nitrate_mgL"]},
            },
        })
    return JSONResponse(clean({"type": "FeatureCollection", "features": feats}))


@app.get("/fhir/Observation/{siteCode}")
def fhir_observation(siteCode: str):
    """Composite risk as an HL7 FHIR R4 Observation (demonstration mapping)."""
    df = _df()
    row = df[df["siteCode"] == siteCode]
    if row.empty:
        raise HTTPException(404, f"Unknown siteCode {siteCode}")
    r = row.iloc[0]
    val = r.get("healthRiskScore")
    if val is None or val != val:
        raise HTTPException(404, f"No risk measurement for {siteCode}")
    return clean({
        "resourceType": "Observation",
        "id": f"aquasentinel-{siteCode}",
        "status": "preliminary",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "environment", "display": "Environmental"}]}],
        "code": {"text": "Urban stream composite health-risk score",
                 "coding": [{"system": "https://aquasentinel.example/oah",
                             "code": "composite-health-risk",
                             "display": "Composite stream health-risk (One Health)"}]},
        "subject": {"display": f"{r['name']} ({siteCode}), {r['city_name']}"},
        "effectiveDateTime": (str(r.get("samplingDate"))[:10]
                              if r.get("samplingDate") == r.get("samplingDate") else None),
        "valueQuantity": {"value": round(float(val), 4), "unit": "scaled index (0-1)"},
        "component": [
            {"code": {"text": _OBS_PROPS[c][0]},
             "valueQuantity": {"value": round(float(r[c]), 4), "unit": "0-1"}}
            for c in RISK_COMPONENTS if r.get(c) == r.get(c)
        ],
        "note": [{"text": "Screening/prioritisation measure. Not a clinical diagnosis."}],
    })


@app.get("/data-dictionary")
def data_dictionary():
    dd = ROOT / "docs" / "data_dictionary.md"
    return {"markdown": dd.read_text() if dd.exists() else "See docs/data_dictionary.md"}


def _num(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return v if isinstance(v, str) else None

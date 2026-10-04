"""Smoke tests for the interoperability API."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

client = TestClient(app)


def test_sensorthings_things_cover_every_site():
    body = client.get("/v1.1/Things").json()
    assert body["@iot.count"] == 106
    assert body["value"][0]["Locations"][0]["location"]["type"] == "Point"


def test_geojson_is_a_feature_collection():
    body = client.get("/geojson/sites").json()
    assert body["type"] == "FeatureCollection" and len(body["features"]) == 106


def test_fhir_observation_has_three_components():
    body = client.get("/fhir/Observation/C5").json()
    assert body["resourceType"] == "Observation"
    assert len(body["component"]) == 3
    assert client.get("/fhir/Observation/NOPE").status_code == 404


def test_citizen_quality_endpoint_matches_validator():
    body = client.get("/citizen/quality").json()
    assert body["summary"]["n_total"] == len(body["value"]) == 71


def test_insights_endpoint_filters_by_verdict():
    r = client.get("/insights")
    if r.status_code == 503:        # outputs not generated yet
        pytest.skip("run `make insights` first")
    body = r.json()
    assert sum(body["counts"].values()) == body["@iot.count"]
    supported = client.get("/insights?status=supported").json()
    assert supported["@iot.count"] == body["counts"]["supported"]


def test_plan_endpoint_lists_sites_and_gaps():
    r = client.get("/plan")
    if r.status_code == 503:
        pytest.skip("run `make insights` first")
    body = r.json()
    assert body["@iot.count"] == len(body["value"]) > 0
    assert all(row["reasons"] for row in body["value"])
    assert any(g["id"] == "INS-ARG-01" for g in body["evidence_gaps"])

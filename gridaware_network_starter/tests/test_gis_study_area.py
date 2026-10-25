"""GIS study-area and circuit filter tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app

GIS = Path(__file__).resolve().parents[2] / "data" / "processed" / "gis.db"
CONFIG = Path(__file__).resolve().parents[2] / "config" / "study_area.json"
STUDY_CIRCUIT = "0000005"
DEMO_KEY = "eo_isolating_eqpt_inst*321305938"


pytestmark = pytest.mark.skipif(
    not GIS.exists() and not CONFIG.exists(),
    reason="GIS or study config not present",
)


@pytest.fixture
def client():
    return TestClient(app)


def test_study_area_endpoint(client: TestClient):
    r = client.get("/gis/study-area")
    assert r.status_code == 200
    body = r.json()
    assert body["selected_circuit_id"] == STUDY_CIRCUIT
    assert body["bounds_wgs84"]["min_lng"] < body["bounds_wgs84"]["max_lng"]
    assert (
        body["counts"]["demo_recloser_dependent_premises"] == 2811
        or body["counts"].get("demo_recloser_dependent_premises") == 2811
    )


def test_features_circuit_filter_primary(client: TestClient):
    r = client.get(
        "/gis/features",
        params={"layer": "primary", "circuit": STUDY_CIRCUIT, "limit": 8000},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["returned"] > 0
    assert body["returned"] <= 905 + 50  # known circuit size + slack
    assert "circuit" in (body.get("filter_note") or "").lower()


def test_scenario_still_full_dependency_set(client: TestClient):
    r = client.get(
        "/scenarios/device-unavailable/summary",
        params={"device_key": DEMO_KEY},
    )
    assert r.status_code == 200
    assert r.json()["modeled_potential_exposure_count"] == 2811

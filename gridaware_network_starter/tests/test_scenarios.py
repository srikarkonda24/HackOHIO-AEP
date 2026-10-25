"""Scenario exposure API tests (requires network.db)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app

DEMO_KEY = "eo_isolating_eqpt_inst*321305938"
EXPECTED_EXPOSURE = 2811
DB = Path(__file__).resolve().parents[1] / "network.db"


pytestmark = pytest.mark.skipif(
    not DB.exists(), reason="network.db not present locally"
)


@pytest.fixture
def client():
    return TestClient(app)


def test_device_unavailable_summary_count(client: TestClient):
    r = client.get(
        "/scenarios/device-unavailable/summary",
        params={"device_key": DEMO_KEY},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_type"] == "device_unavailable"
    assert body["modeled_potential_exposure_count"] == EXPECTED_EXPOSURE
    assert body["premise_count"] == EXPECTED_EXPOSURE
    assert len(body["premise_ids"]) == EXPECTED_EXPOSURE
    assert "customers" not in body
    assert "Simulated" in body["disclaimer"] or "simulated" in body["disclaimer"].lower()


def test_device_unavailable_full_geo_matches_count(client: TestClient):
    r = client.get(
        "/scenarios/device-unavailable",
        params={"device_key": DEMO_KEY},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["modeled_potential_exposure_count"] == EXPECTED_EXPOSURE
    assert body["returned_customer_points"] == EXPECTED_EXPOSURE
    assert len(body["customers"]) == EXPECTED_EXPOSURE
    sample = body["customers"][0]
    assert {"premise_id", "longitude", "latitude", "circuit_id"} <= sample.keys()


def test_unknown_device_returns_404(client: TestClient):
    r = client.get(
        "/scenarios/device-unavailable",
        params={"device_key": "missing*device"},
    )
    assert r.status_code == 404


def test_summary_and_full_share_premise_ids(client: TestClient):
    summary = client.get(
        "/scenarios/device-unavailable/summary",
        params={"device_key": DEMO_KEY},
    ).json()
    full = client.get(
        "/scenarios/device-unavailable",
        params={"device_key": DEMO_KEY},
    ).json()
    assert summary["premise_ids"] == full["premise_ids"]
    assert set(summary["premise_ids"]) == {
        c["premise_id"] for c in full["customers"]
    }


def test_scenario_response_shape_for_future_multi_device(client: TestClient):
    body = client.get(
        "/scenarios/device-unavailable/summary",
        params={"device_key": DEMO_KEY},
    ).json()
    assert body["scenario_type"] == "device_unavailable"
    assert isinstance(body["device_key"], str)
    assert isinstance(body["premise_ids"], list)
    assert "device" in body and "device_type" in body["device"]


def test_existing_impact_endpoint_unchanged(client: TestClient):
    r = client.get(
        "/devices/impact",
        params={"device_key": DEMO_KEY, "limit": 5000},
    )
    assert r.status_code == 200
    assert r.json()["potentially_dependent_premises"] == EXPECTED_EXPOSURE

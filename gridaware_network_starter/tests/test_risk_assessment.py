"""Historical weather risk assessment tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app
from historical_weather_risk import classify_relative_risk, load_model

DB = Path(__file__).resolve().parents[1] / "network.db"
PID = "000052580"
MODEL = Path(__file__).resolve().parents[2] / "config" / "risk_model" / "historical_weather_risk_model.json"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="network.db not present")


@pytest.fixture
def client():
    return TestClient(app)


def _post(client, premise_id: str, **weather):
    return client.post(f"/customers/{premise_id}/risk-assessment", json=weather)


def test_calm_conditions_low(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=12,
        total_precipitation_in=0.01,
        min_temperature_f=55,
        snowfall_in=0,
    )
    assert r.status_code == 200
    assert r.json()["relative_risk"] == "LOW"


def test_strong_wind_not_low(client: TestClient):
    mild = _post(
        client,
        PID,
        max_wind_gust_mph=20,
        total_precipitation_in=0.05,
        min_temperature_f=50,
        snowfall_in=0,
    ).json()
    strong = _post(
        client,
        PID,
        max_wind_gust_mph=46,
        total_precipitation_in=0.05,
        min_temperature_f=50,
        snowfall_in=0,
    ).json()
    assert strong["relative_risk"] in ("MEDIUM", "HIGH")
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    assert order[strong["relative_risk"]] >= order[mild["relative_risk"]]


def test_monotonic_wind_holding_other_inputs_fixed():
    base = dict(
        total_precipitation_in=0.1,
        min_temperature_f=45,
        snowfall_in=0,
    )
    prev = "LOW"
    for wind in [10, 20, 30, 35, 41, 45, 50]:
        risk, _, _ = classify_relative_risk(max_wind_gust_mph=float(wind), **base)
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        assert order[risk] >= order[prev]
        prev = risk


def test_heavy_precipitation_elevates_concern(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=25,
        total_precipitation_in=1.5,
        min_temperature_f=40,
        snowfall_in=0,
    )
    assert r.status_code == 200
    assert r.json()["relative_risk"] in ("MEDIUM", "HIGH")


def test_freezing_weather(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=28,
        total_precipitation_in=0.3,
        min_temperature_f=25,
        snowfall_in=0,
    )
    body = r.json()
    assert body["relative_risk"] in ("LOW", "MEDIUM", "HIGH")
    assert body["active_weather_condition_flags"]["freezing"] is True


def test_snowfall_winter_compound(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=35,
        total_precipitation_in=0.4,
        min_temperature_f=28,
        snowfall_in=3,
    )
    body = r.json()
    assert body["relative_risk"] in ("MEDIUM", "HIGH")
    assert body["assessment_type"] == "historical_weather_informed_relative_outage_risk"


def test_combined_severe_high(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=48,
        total_precipitation_in=1.2,
        min_temperature_f=30,
        snowfall_in=2,
    )
    assert r.json()["relative_risk"] == "HIGH"


def test_identical_inputs_reproducible(client: TestClient):
    payload = dict(
        max_wind_gust_mph=33,
        total_precipitation_in=0.5,
        min_temperature_f=35,
        snowfall_in=0.5,
    )
    a = _post(client, PID, **payload).json()
    b = _post(client, PID, **payload).json()
    assert a["relative_risk"] == b["relative_risk"]
    assert a["hazard_score"] == b["hazard_score"]


def test_invalid_premise_404(client: TestClient):
    r = _post(
        client,
        "__no_such__",
        max_wind_gust_mph=10,
        total_precipitation_in=0,
        min_temperature_f=50,
        snowfall_in=0,
    )
    assert r.status_code == 404


def test_invalid_numeric_values_422(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=-5,
        total_precipitation_in=0,
        min_temperature_f=50,
        snowfall_in=0,
    )
    assert r.status_code == 422


def test_real_premise_includes_infrastructure_context(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=15,
        total_precipitation_in=0.02,
        min_temperature_f=60,
        snowfall_in=0,
    )
    body = r.json()
    assert body["premise_id"] == PID
    assert body["location"]["weather_sample_location"] == "vinton_customer"
    assert body["infrastructure_context_summary"]
    assert "not a verified outage probability" in body["explanation"].lower()


def test_no_outage_probability_in_response(client: TestClient):
    r = _post(
        client,
        PID,
        max_wind_gust_mph=45,
        total_precipitation_in=1.0,
        min_temperature_f=32,
        snowfall_in=1,
    )
    text = str(r.json())
    assert "%" not in text


@pytest.mark.parametrize(
    "score_expectation,weather",
    [
        ("LOW", dict(max_wind_gust_mph=15, total_precipitation_in=0.01, min_temperature_f=60, snowfall_in=0)),
        ("MEDIUM", dict(max_wind_gust_mph=42, total_precipitation_in=0.15, min_temperature_f=45, snowfall_in=0)),
        ("HIGH", dict(max_wind_gust_mph=50, total_precipitation_in=1.5, min_temperature_f=28, snowfall_in=4)),
    ],
)
def test_lmh_boundary_examples(client: TestClient, score_expectation, weather):
    r = _post(client, PID, **weather)
    assert r.json()["relative_risk"] == score_expectation


def test_model_constants_file_present():
    assert MODEL.is_file()
    model = load_model()
    assert model["enrichment_analysis_thresholds"]["max_wind_gust_mph_gte"] == 40.5

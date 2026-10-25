"""Stage 6 proactive alert rules."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from alert_engine import (
    evaluate_restoration_committed,
    evaluate_restoration_playback,
)
from alert_session_store import reset_session
from api import app

DB = Path(__file__).resolve().parents[1] / "network.db"
PID = "000052580"
SID = "test-alert-session"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="network.db not present")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_session():
    reset_session(SID)
    yield
    reset_session(SID)


def _storm_high():
    return {
        "max_wind_gust_mph": 55,
        "total_precipitation_in": 1.2,
        "min_temperature_f": 28,
        "snowfall_in": 2,
    }


def _storm_low():
    return {
        "max_wind_gust_mph": 12,
        "total_precipitation_in": 0.01,
        "min_temperature_f": 60,
        "snowfall_in": 0,
    }


def test_high_risk_creates_preparation_alert(client: TestClient):
    r = client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": _storm_high()},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is True
    events = [e for e in body["session"]["events"] if e["status"] == "previewed"]
    assert any(e["alert_type"] == "storm_preparation" for e in events)
    assert body["relative_risk"] == "HIGH"


def test_low_risk_no_preparation_alert(client: TestClient):
    r = client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": _storm_low()},
    )
    assert r.status_code == 200
    assert r.json()["created"] is False
    preview = [e for e in r.json()["session"]["events"] if e["status"] == "previewed"]
    assert not preview


def test_medium_risk_requires_opt_in(client: TestClient):
    medium = {
        "max_wind_gust_mph": 35,
        "total_precipitation_in": 0.4,
        "min_temperature_f": 40,
        "snowfall_in": 0,
    }
    client.put(
        f"/alerts/session/{SID}/preferences",
        json={
            "notifications_enabled": True,
            "channel": "in_app",
            "medium_risk_preparation": False,
        },
    )
    r1 = client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": medium},
    )
    if r1.json()["relative_risk"] == "MEDIUM":
        assert r1.json()["created"] is False
    client.put(
        f"/alerts/session/{SID}/preferences",
        json={
            "notifications_enabled": True,
            "channel": "in_app",
            "medium_risk_preparation": True,
        },
    )
    reset_session(SID)
    client.put(
        f"/alerts/session/{SID}/preferences",
        json={
            "notifications_enabled": True,
            "channel": "in_app",
            "medium_risk_preparation": True,
        },
    )
    r2 = client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": medium},
    )
    assert r2.status_code == 200
    risk = r2.json()["relative_risk"]
    if risk == "MEDIUM":
        assert r2.json()["created"] is True
    elif risk == "HIGH":
        assert r2.json()["created"] is True


def test_notifications_disabled(client: TestClient):
    client.put(
        f"/alerts/session/{SID}/preferences",
        json={
            "notifications_enabled": False,
            "channel": "sms",
            "medium_risk_preparation": True,
        },
    )
    r = client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": _storm_high()},
    )
    assert r.json()["created"] is False


def test_outage_transition_once():
    sess = reset_session("unit-outage")
    snap_out = {"simulated_outage_group_ids": ["RES1"], "powered_group_ids": []}
    snap_powered = {"simulated_outage_group_ids": [], "powered_group_ids": ["RES1"]}
    evaluate_restoration_committed(
        sess,
        sim_run_id="sim-a",
        initial_snapshot=snap_powered,
        group_restoration_times={"RES1": 0},
        modeled_group_id="RES1",
    )
    r1 = evaluate_restoration_committed(
        sess,
        sim_run_id="sim-b",
        initial_snapshot=snap_out,
        group_restoration_times={"RES1": 10},
        modeled_group_id="RES1",
    )
    assert len(r1["created_events"]) == 1
    r2 = evaluate_restoration_committed(
        sess,
        sim_run_id="sim-b",
        initial_snapshot=snap_out,
        group_restoration_times={"RES1": 10},
        modeled_group_id="RES1",
    )
    assert len(r2["created_events"]) == 0


def test_eta_update_only_on_category_change():
    sess = reset_session("unit-eta")
    out = {"simulated_outage_group_ids": ["RES1"], "powered_group_ids": []}
    evaluate_restoration_committed(
        sess,
        sim_run_id="sim-1",
        initial_snapshot=out,
        group_restoration_times={"RES1": 20},
        modeled_group_id="RES1",
    )
    r_same = evaluate_restoration_committed(
        sess,
        sim_run_id="sim-2",
        initial_snapshot=out,
        group_restoration_times={"RES1": 22},
        modeled_group_id="RES1",
    )
    assert not any(e["alert_type"] == "eta_update" for e in r_same["created_events"])
    r_change = evaluate_restoration_committed(
        sess,
        sim_run_id="sim-3",
        initial_snapshot=out,
        group_restoration_times={"RES1": 30},
        modeled_group_id="RES1",
    )
    assert any(e["alert_type"] == "eta_update" for e in r_change["created_events"])


def test_restoration_playback_not_before_restore():
    sess = reset_session("unit-restore")
    sess.restoration.last_sim_run_id = "sim-x"
    sess.restoration.home_restore_time_hours = 8.0
    early = evaluate_restoration_playback(
        sess,
        sim_run_id="sim-x",
        playback_time_hours=2,
        modeled_group_id="RES1",
        timeline=[{"event": "group_restored", "group_id": "RES1", "time_hours": 8}],
    )
    assert early["created"] is False
    late = evaluate_restoration_playback(
        sess,
        sim_run_id="sim-x",
        playback_time_hours=8.5,
        modeled_group_id="RES1",
        timeline=[{"event": "group_restored", "group_id": "RES1", "time_hours": 8}],
    )
    assert late["created"] is True
    again = evaluate_restoration_playback(
        sess,
        sim_run_id="sim-x",
        playback_time_hours=9,
        modeled_group_id="RES1",
        timeline=[],
    )
    assert again["created"] is False


def test_reset_clears_events(client: TestClient):
    client.post(
        f"/alerts/session/{SID}/evaluate/risk-preparation",
        json={"premise_id": PID, "storm_scenario": _storm_high()},
    )
    r = client.post(f"/alerts/session/{SID}/reset")
    assert r.status_code == 200
    assert r.json()["events"] == []

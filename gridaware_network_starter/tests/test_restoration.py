"""Restoration simulation tests (Level 4 graph + switching)."""
import pytest
from fastapi.testclient import TestClient

from api import app
from repair_labor import load_labor_config, repair_duration_hours
from restoration_graph import (
    is_group_connected,
    is_group_connected_legacy,
    load_network,
    new_state,
    snapshot_from_state,
)
from restoration_actions import apply_switch_action, switching_preconditions_met
from restoration_eta_display import (
    format_customer_restoration_eta,
    restoration_hours_to_category,
)
from restoration_optimizer import run_restoration_scenario


@pytest.fixture
def client():
    return TestClient(app)


def test_one_damaged_upstream_disconnects_all():
    net = load_network()
    snap = snapshot_from_state(net, new_state(net, {"A"}))
    assert set(snap["simulated_outage_group_ids"]) == {
        "HOSPITAL",
        "FIRE",
        "RES1",
        "RES2",
        "RES3",
    }


def test_downstream_repair_cannot_bypass_upstream():
    net = load_network()
    state = new_state(net, {"A", "B"})
    state.repaired.add("B")
    assert not is_group_connected(net, "HOSPITAL", state)


def test_restore_upstream_then_downstream():
    net = load_network()
    state = new_state(net, {"A", "B"})
    state.repaired.update({"A", "B"})
    assert is_group_connected(net, "HOSPITAL", state)


def test_trunk_damage_hospital_may_stay_powered():
    net = load_network()
    snap = snapshot_from_state(net, new_state(net, {"D"}))
    assert "HOSPITAL" in snap["powered_group_ids"]
    assert "RES1" in snap["simulated_outage_group_ids"]


def test_switching_invalid_without_open_s1():
    net = load_network()
    state = new_state(net, {"B"})
    close = next(a for a in net["switching_actions"] if a["id"] == "CLOSE_S2")
    ok, _ = switching_preconditions_met(net, close, state)
    assert ok is False


def test_no_power_without_source_path():
    net = load_network()
    state = new_state(net, {"A", "D"})
    assert not is_group_connected(net, "RES1", state)


def test_step_restoration_before_repair(client: TestClient):
    r = client.post(
        "/restoration/simulate",
        json={
            "damaged_component_ids": ["B"],
            "total_workers": 12,
            "workers_per_crew": 4,
            "enable_step_restoration": True,
        },
    )
    body = r.json()
    assert body["comparison"]["hospital_restore_delta_hours"] > 0
    step_h = body["step_restoration_optimized"]["group_restoration_times"]["HOSPITAL"]
    repair_h = body["repair_only_optimized"]["group_restoration_times"]["HOSPITAL"]
    assert step_h < repair_h


def test_no_damage_all_powered(client: TestClient):
    r = client.post(
        "/restoration/simulate",
        json={
            "damaged_component_ids": [],
            "total_workers": 8,
            "workers_per_crew": 4,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["initial_snapshot"]["simulated_outage_group_ids"] == []


def test_labor_duration_formula():
    cfg = load_labor_config()
    assert "fixture" not in str(cfg.get("source_workbook", "")).lower()
    assert "synthetic" not in str(cfg.get("data_provenance", "")).lower()
    pole = repair_duration_hours("pole_replacement", workers_per_crew=4, config=cfg)
    entry = cfg["repairs"]["pole_replacement"]
    direct = entry["removal_person_hours"] + entry["installation_person_hours"]
    assert pole["central_repair_hours"] == pytest.approx(direct * 4.5 / 4, rel=1e-3)
    assert cfg["source_workbook"] == "Install_Labor_HackOHIO.xlsx"


def test_labor_from_aep_workbook(client: TestClient):
    r = client.get("/restoration/network")
    refs = r.json()["labor_references"]
    assert refs.get("synthetic_labor_warning") is False
    assert "Install_Labor_HackOHIO.xlsx" in str(refs.get("source_workbook", ""))


def test_invalid_component(client: TestClient):
    r = client.post(
        "/restoration/simulate",
        json={"damaged_component_ids": ["Z"], "total_workers": 8, "workers_per_crew": 4},
    )
    assert r.status_code == 400


def test_worker_limits(client: TestClient):
    r = client.post(
        "/restoration/simulate",
        json={"damaged_component_ids": ["A"], "total_workers": 3, "workers_per_crew": 4},
    )
    assert r.status_code == 400


def test_restoration_eta_category_boundaries():
    assert restoration_hours_to_category(3) == "Within 1 day"
    assert restoration_hours_to_category(24) == "Within 1 day"
    assert restoration_hours_to_category(24.0001) == "1–2 days"
    assert restoration_hours_to_category(48) == "1–2 days"
    assert restoration_hours_to_category(48.0001) == "2–3 days"
    assert restoration_hours_to_category(72) == "2–3 days"
    assert restoration_hours_to_category(72.0001) == "3–4 days"
    assert restoration_hours_to_category(96) == "3–4 days"
    assert restoration_hours_to_category(96.0001) == "4–5 days"
    assert restoration_hours_to_category(120) == "4–5 days"
    assert restoration_hours_to_category(120.0001) == "5–7 days (within 1 week)"
    assert restoration_hours_to_category(168) == "5–7 days (within 1 week)"
    assert restoration_hours_to_category(168.0001) == "More than 1 week"


def test_customer_restoration_eta_no_outage_when_powered():
    assert (
        format_customer_restoration_eta(
            is_initially_powered=True,
            restoration_hours=0.0,
        )
        == "No simulated outage"
    )


def test_network_endpoint(client: TestClient):
    r = client.get("/restoration/network")
    assert r.status_code == 200
    assert len(r.json()["network"]["components"]) >= 6


def test_outage_preview(client: TestClient):
    r = client.post(
        "/restoration/outage-preview",
        json={"damaged_component_ids": ["B"]},
    )
    assert r.status_code == 200
    out = r.json()["snapshot"]["simulated_outage_group_ids"]
    assert "HOSPITAL" in out


def test_multi_damage_upstream_order(client: TestClient):
    """G and A damaged must schedule without raw infeasible errors."""
    r = client.post(
        "/restoration/simulate",
        json={
            "damaged_component_ids": ["G", "A"],
            "total_workers": 12,
            "workers_per_crew": 4,
            "baseline_repair_order": ["G", "A"],
            "enable_step_restoration": True,
        },
    )
    assert r.status_code == 200
    assert r.json()["step_restoration_optimized"] is not None


def test_storm_major_increases_repair_scope_not_ilm():
    labor = load_labor_config()
    minor = run_restoration_scenario(
        damaged_component_ids=["D"],
        total_workers=4,
        workers_per_crew=4,
        damage_severity="minor",
        access_conditions="normal",
    )
    major = run_restoration_scenario(
        damaged_component_ids=["D"],
        total_workers=4,
        workers_per_crew=4,
        damage_severity="major",
        access_conditions="normal",
    )
    base = repair_duration_hours("wire_replacement", workers_per_crew=4, quantity=1.0, config=labor)
    double = repair_duration_hours("wire_replacement", workers_per_crew=4, quantity=2.0, config=labor)
    assert double["central_repair_hours"] == pytest.approx(base["central_repair_hours"] * 2, rel=1e-4)
    m_hours = major["step_restoration_optimized"]["group_restoration_times"]["RES1"]
    n_hours = minor["step_restoration_optimized"]["group_restoration_times"]["RES1"]
    assert m_hours > n_hours


def test_restricted_access_delays_start_not_labor_hours():
    labor = load_labor_config()
    base = repair_duration_hours("pole_replacement", workers_per_crew=4, quantity=1.0, config=labor)
    normal = run_restoration_scenario(
        damaged_component_ids=["A"],
        total_workers=4,
        workers_per_crew=4,
        access_conditions="normal",
    )
    restricted = run_restoration_scenario(
        damaged_component_ids=["A"],
        total_workers=4,
        workers_per_crew=4,
        access_conditions="restricted",
    )
    n_tl = normal["step_restoration_optimized"]["timeline"]
    r_tl = restricted["step_restoration_optimized"]["timeline"]
    n_repair = next(t for t in n_tl if t["event"] == "repair_complete")
    r_repair = next(t for t in r_tl if t["event"] == "repair_complete")
    assert n_repair["labor"]["central_repair_hours"] == pytest.approx(
        base["central_repair_hours"], rel=1e-3
    )
    assert r_repair["labor"]["central_repair_hours"] == pytest.approx(
        base["central_repair_hours"], rel=1e-3
    )
    assert r_repair["start_hours"] > n_repair["start_hours"]
    assert r_repair["finish_hours"] > n_repair["finish_hours"]


def test_multiday_home_eta_when_storm_scope_and_access():
    out = run_restoration_scenario(
        damaged_component_ids=["A", "B", "C", "D", "E", "F", "G"],
        total_workers=4,
        workers_per_crew=4,
        damage_severity="major",
        access_conditions="restricted",
    )
    home = out["modeled_home_restore_hours"]
    assert home is not None
    assert home > 24
    assert restoration_hours_to_category(home) in (
        "1–2 days",
        "2–3 days",
        "3–4 days",
        "4–5 days",
        "5–7 days (within 1 week)",
        "More than 1 week",
    )


def test_within_one_day_minor_single_home_damage():
    out = run_restoration_scenario(
        damaged_component_ids=["C"],
        total_workers=12,
        workers_per_crew=4,
        damage_severity="minor",
        access_conditions="normal",
    )
    home = out["modeled_home_restore_hours"]
    assert home is not None
    assert home <= 24
    assert restoration_hours_to_category(home) == "Within 1 day"


def test_storm_api_fields(client: TestClient):
    r = client.post(
        "/restoration/simulate",
        json={
            "damaged_component_ids": ["C"],
            "total_workers": 8,
            "workers_per_crew": 4,
            "damage_severity": "moderate",
            "access_conditions": "difficult",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["storm_context"]["damage_severity"] == "moderate"
    assert body["labor_preview"]


def test_risk_assessment_regression(client: TestClient):
    r = client.post(
        "/customers/000052580/risk-assessment",
        json={
            "max_wind_gust_mph": 15,
            "total_precipitation_in": 0.02,
            "min_temperature_f": 58,
            "snowfall_in": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["relative_risk"] == "LOW"

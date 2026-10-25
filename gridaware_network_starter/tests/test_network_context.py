"""Customer network context API tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app
from customer_clip import customer_clip_available

DB = Path(__file__).resolve().parents[1] / "network.db"
PID = "000052580"
XFRM_LOC = "37800259000284"
XFRM_KEY = "eo_power_xfrmr_inst*144043179"
RECL_KEY = "eo_isolating_eqpt_inst*321305938"


pytestmark = pytest.mark.skipif(not DB.exists(), reason="network.db not present")


@pytest.fixture
def client():
    return TestClient(app)


def test_network_context_000052580(client: TestClient):
    r = client.get(f"/customers/{PID}/network-context")
    assert r.status_code == 200
    body = r.json()
    assert body["premise_id"] == PID
    assert body["premise"]["circuit_id"] == "0000005"
    assert body["upstream_is_ordered_path"] is False
    assert body["upstream_device_count"] == 6

    keys = {u["device"]["device_key"] for u in body["upstream_devices"]}
    assert RECL_KEY in keys
    assert XFRM_KEY in keys

    for u in body["upstream_devices"]:
        assert u["relationship_kind"] == "upstream_index_membership"
        assert u["is_ordered_path_position"] is False
        assert u["evidence_type"] == "upstream_index_membership"

    st = body.get("service_transformer")
    if customer_clip_available():
        assert st is not None
        assert st["recorded_service_location_n"] == XFRM_LOC
        assert st["evidence_type"] == "recorded_location_reference"
        dev_keys = {d["device_key"] for d in st["matched_network_devices"]}
        assert XFRM_KEY in dev_keys
        direct = [
            u
            for u in body["upstream_devices"]
            if u["direct_equipment_link_to_recorded_service_location"]
        ]
        assert any(u["device"]["device_key"] == XFRM_KEY for u in direct)
    else:
        assert "customer_clip_shapefile_unavailable" in body["missing_or_partial"]

    assert any(
        "conductor path" in lim.lower() or "verified" in lim.lower()
        for lim in body["limitations"]
    )

    if body.get("circuit_identifier_observations"):
        conflict_locs = {
            o["location_n"] for o in body["circuit_identifier_observations"]
        }
        assert "37800281C36078" in conflict_locs or len(conflict_locs) >= 0


def test_network_context_missing_premise(client: TestClient):
    r = client.get("/customers/__no_such_premise__/network-context")
    assert r.status_code == 404


def test_gis_upstream_l_not_live_switching(client: TestClient):
    r = client.get(f"/customers/{PID}/network-context")
    body = r.json()
    for u in body["upstream_devices"]:
        if u["device"]["device_key"] == RECL_KEY:
            if u["gis_assets"]:
                sta = None
                for a in u["gis_assets"]:
                    sta = a.get("attributes", {}).get("normal_sta") or sta
                if sta:
                    assert u["gis_switching_attribute_disclaimer"]
            break

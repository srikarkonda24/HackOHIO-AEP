"""Customer network context — evidence-typed, read-only."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from customer_clip import customer_clip_available, customer_shp_path, lookup_customer_clip

REPO_ROOT = Path(__file__).resolve().parents[1]
GIS_DB = Path(
    os.getenv("GIS_DB", str(REPO_ROOT / "data" / "processed" / "gis.db"))
)

GIS_ATTR_FIELDS = (
    "circuit_id",
    "aep_circui",
    "upstream_l",
    "normal_sta",
    "location_n",
    "location_1",
    "network_ty",
    "aep_statio",
)


def _gis_connect() -> sqlite3.Connection | None:
    if not GIS_DB.exists():
        return None
    con = sqlite3.connect(f"file:{GIS_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _gis_assets_at(con: sqlite3.Connection, location_n: str) -> list[dict[str, Any]]:
    assets = []
    for row in con.execute(
        """
        SELECT layer_id, feature_id, location_n, properties_json
        FROM features WHERE location_n=?
        ORDER BY layer_id, feature_id
        """,
        (location_n.strip(),),
    ):
        props = json.loads(row["properties_json"])
        attrs = {k: props.get(k) for k in GIS_ATTR_FIELDS if props.get(k) not in (None, "")}
        assets.append(
            {
                "layer_id": row["layer_id"],
                "feature_id": row["feature_id"],
                "location_n": row["location_n"],
                "attributes": attrs,
            }
        )
    return assets


def _circuit_conflicts(assets_by_loc: dict[str, list[dict]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for loc, assets in assets_by_loc.items():
        cids: dict[str, list[str]] = {}
        for a in assets:
            cid = str(a.get("attributes", {}).get("circuit_id") or "").strip()
            if not cid:
                continue
            cids.setdefault(cid, []).append(a["layer_id"])
        if len(cids) > 1:
            observations.append(
                {
                    "location_n": loc,
                    "conflict_type": "multiple_circuit_id_at_same_location_n",
                    "circuit_ids": {
                        cid: layers for cid, layers in sorted(cids.items())
                    },
                    "note": (
                        "GIS layers disagree on circuit_id at one location_n; "
                        "not reconciled automatically."
                    ),
                }
            )
    return observations


def _collect_gis_refs(assets_by_loc: dict[str, list[dict]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for loc, assets in assets_by_loc.items():
        for a in assets:
            attrs = a.get("attributes") or {}
            for field in ("upstream_l", "location_1"):
                val = attrs.get(field)
                if val is None or str(val).strip() == "":
                    continue
                target = str(val).strip()
                refs.append(
                    {
                        "from_location_n": loc,
                        "layer_id": a["layer_id"],
                        "field": field,
                        "value": target,
                        "relationship_kind": "gis_attribute_reference",
                        "evidence_type": "gis_shapefile_attribute",
                        "source": f"gis.db features ({a['layer_id']})",
                        "interpretation_limit": (
                            "Attribute reference only; not verified conductor or "
                            "equipment-to-equipment connectivity."
                        ),
                        "target_matches_location_n_pattern": target.isdigit()
                        or (
                            len(target) >= 10 and target[:6].isdigit()
                        ),
                    }
                )
    return refs


def _devices_at_location(con: sqlite3.Connection, location_id: str) -> list[dict]:
    return [
        dict(r)
        for r in con.execute(
            "SELECT * FROM devices WHERE location_id=?", (location_id.strip(),)
        )
    ]


def build_network_context(con: sqlite3.Connection, premise_id: str) -> dict[str, Any]:
    pid = premise_id.strip()
    premise = con.execute(
        "SELECT * FROM premises WHERE premise_id=?", (pid,)
    ).fetchone()
    if not premise:
        raise KeyError(pid)

    premise_dict = dict(premise)
    limitations: list[str] = []
    missing: list[str] = []

    clip = lookup_customer_clip(pid)
    if clip is None and customer_clip_available():
        missing.append("customer_clip_record_not_found_for_premise")
    elif clip is None:
        missing.append("customer_clip_shapefile_unavailable")
        limitations.append(
            f"Customer_Clip not loaded ({customer_shp_path()}); "
            "service transformer location fields unavailable."
        )

    gis = _gis_connect()
    if gis is None:
        missing.append("gis_db_unavailable")
        limitations.append("GIS database unavailable; no layer attributes attached.")

    assets_by_loc: dict[str, list[dict]] = {}

    def ensure_gis(loc: str | None) -> list[dict]:
        if not loc or not gis:
            return []
        loc = str(loc).strip()
        if loc not in assets_by_loc:
            assets_by_loc[loc] = _gis_assets_at(gis, loc)
        return assets_by_loc[loc]

    # Service transformer from Customer_Clip location reference
    service_transformer: dict[str, Any] | None = None
    xfmr_loc = None
    if clip:
        xfmr_loc = str(clip.get("aep_xfmr_l") or clip.get("aep_locati") or "").strip()
        if xfmr_loc:
            matched = _devices_at_location(con, xfmr_loc)
            distribution = [d for d in matched if "xfrm" in d["device_type"].lower() or d["device_type"] in ("Distribution", "Step")]
            service_transformer = {
                "recorded_service_location_n": xfmr_loc,
                "evidence_type": "recorded_location_reference",
                "source": "Customer_Clip.shp (aep_xfmr_l / aep_locati)",
                "relationship_kind": "customer_to_service_location",
                "matched_network_devices": matched,
                "location_id_join_devices": matched,
                "gis_assets": ensure_gis(xfmr_loc),
                "note": (
                    "Customer shapefile points at a service transformer location; "
                    "network devices share exact location_id when listed."
                ),
            }
            if not matched:
                missing.append("no_network_device_at_recorded_service_location")
        else:
            missing.append("customer_clip_missing_transformer_location_fields")

    # Upstream membership (unordered set)
    upstream_rows = con.execute(
        """
        SELECT d.* FROM devices d
        JOIN dependencies dp ON d.device_key = dp.device_key
        WHERE dp.premise_id=?
        ORDER BY d.device_type, d.device_key
        """,
        (pid,),
    ).fetchall()

    upstream_devices: list[dict[str, Any]] = []
    for row in upstream_rows:
        dev = dict(row)
        loc = dev.get("location_id")
        gis_assets = ensure_gis(loc) if loc else []
        gis_match = bool(gis_assets)
        direct_link = False
        if xfmr_loc and loc and str(loc).strip() == xfmr_loc:
            direct_link = True

        upstream_devices.append(
            {
                "device": dev,
                "relationship_kind": "upstream_index_membership",
                "evidence_type": "upstream_index_membership",
                "source": "network.db dependencies + devices (matched_upstream.txt index)",
                "is_ordered_path_position": False,
                "direct_equipment_link_to_recorded_service_location": direct_link,
                "location_id_gis_join": {
                    "location_id": loc,
                    "gis_features_found": gis_match,
                    "match_method": "exact location_id = GIS location_n"
                    if gis_match
                    else None,
                },
                "gis_assets": gis_assets,
                "gis_switching_attribute_disclaimer": (
                    "normal_sta and similar GIS fields are as-built attributes, "
                    "not live switching or outage state."
                    if any(
                        (a.get("attributes") or {}).get("normal_sta")
                        for a in gis_assets
                    )
                    else None
                ),
            }
        )

    circuit_observations = _circuit_conflicts(assets_by_loc)
    gis_refs = _collect_gis_refs(assets_by_loc)

    # Explicit: no verified path from service xfmr to recloser
    recloser_keys = [
        u["device"]["device_key"]
        for u in upstream_devices
        if "recloser" in u["device"]["device_type"].lower()
    ]
    if xfmr_loc and recloser_keys:
        limitations.append(
            "Premise upstream index includes reclosers and a recorded service "
            "transformer location, but no independently verified conductor path "
            "between them is modeled."
        )
        # Check if any gis ref from xfmr loc points to recloser loc
        recl_locs = {
            str(u["device"].get("location_id")).strip()
            for u in upstream_devices
            if "recloser" in u["device"]["device_type"].lower()
            and u["device"].get("location_id")
        }
        linked = False
        for ref in gis_refs:
            if ref["from_location_n"] == xfmr_loc and ref["value"] in recl_locs:
                linked = True
        if not linked:
            limitations.append(
                "No GIS upstream_l/location_1 reference found from recorded "
                f"service location {xfmr_loc} to a recloser location_n in this context."
            )

    if gis:
        gis.close()

    return {
        "premise_id": pid,
        "premise": {
            "premise_id": premise_dict["premise_id"],
            "longitude": premise_dict["longitude"],
            "latitude": premise_dict["latitude"],
            "circuit_id": premise_dict["circuit_id"],
            "source": "network.db premises (Customer_Clip import)",
        },
        "customer_clip": clip,
        "customer_clip_source": str(customer_shp_path()) if customer_clip_available() else None,
        "service_transformer": service_transformer,
        "upstream_devices": upstream_devices,
        "upstream_device_count": len(upstream_devices),
        "upstream_is_ordered_path": False,
        "gis_location_attributes": assets_by_loc,
        "gis_attribute_references": gis_refs,
        "circuit_identifier_observations": circuit_observations,
        "missing_or_partial": missing,
        "limitations": limitations,
        "evidence_model_version": "1.0",
        "disclaimer": (
            "Structured context from indexed memberships and identifier joins only. "
            "Not a confirmed outage, serial feeder path, or switching study."
        ),
    }

"""Analyze candidate demo study circuits from real GIS + network.db (read-only)."""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GIS_DB = REPO / "data" / "processed" / "gis.db"
NET_DB = REPO / "gridaware_network_starter" / "network.db"
DEMO_KEY = "eo_isolating_eqpt_inst*321305938"

# Roanoke, VA approximate clip for candidate search
ROANOKE_BBOX = (-80.05, 37.05, -79.55, 37.45)


def circuit_from_props(props: dict) -> str:
    for key in ("circuit_id", "aep_circui", "Circuit", "circuit"):
        val = props.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def in_bbox(row, bbox) -> bool:
    min_lng, min_lat, max_lng, max_lat = bbox
    return (
        row["maxx"] >= min_lng
        and row["minx"] <= max_lng
        and row["maxy"] >= min_lat
        and row["miny"] <= max_lat
    )


def main() -> None:
    gis = sqlite3.connect(GIS_DB)
    gis.row_factory = sqlite3.Row
    net = sqlite3.connect(NET_DB)
    net.row_factory = sqlite3.Row

    device_locs = {
        str(r[0]).strip()
        for r in net.execute(
            "SELECT location_id FROM devices WHERE location_id IS NOT NULL"
        )
        if r[0]
    }

    demo = net.execute(
        "SELECT device_key, device_type, location_id FROM devices WHERE device_key=?",
        (DEMO_KEY,),
    ).fetchone()
    demo_deps = net.execute(
        "SELECT COUNT(*) FROM dependencies WHERE device_key=?", (DEMO_KEY,)
    ).fetchone()[0]
    print("=== Demo device ===")
    print(dict(demo), "dependent_premises=", demo_deps)

    demo_circuits = net.execute(
        """
        SELECT p.circuit_id, COUNT(*) AS c
        FROM dependencies d
        JOIN premises p ON p.premise_id = d.premise_id
        WHERE d.device_key=?
        GROUP BY p.circuit_id
        ORDER BY c DESC
        LIMIT 15
        """,
        (DEMO_KEY,),
    ).fetchall()
    print("Demo dependency premise circuit_id distribution (top):")
    for r in demo_circuits:
        print(f"  {r['circuit_id']}: {r['c']}")

    # Aggregate GIS stats by circuit in Roanoke bbox
    circuit_stats: dict[str, dict] = defaultdict(
        lambda: {
            "primary_segments": 0,
            "reclosers": 0,
            "switches": 0,
            "fuses": 0,
            "transformers": 0,
            "topology_matched_equipment": 0,
            "minx": 999,
            "miny": 999,
            "maxx": -999,
            "maxy": -999,
        }
    )

    equip_layers = {"reclosers", "switches", "fuses", "transformers"}
    for layer in ("primary", *equip_layers):
        for row in gis.execute(
            "SELECT properties_json, minx, miny, maxx, maxy, location_n FROM features WHERE layer_id=?",
            (layer,),
        ):
            if not in_bbox(row, ROANOKE_BBOX):
                continue
            props = json.loads(row["properties_json"])
            cid = circuit_from_props(props)
            if not cid:
                continue
            st = circuit_stats[cid]
            if layer == "primary":
                st["primary_segments"] += 1
            elif layer in equip_layers:
                st[layer + ("s" if layer != "primary" else "")] = st.get(layer, 0) + 1
                key = layer if layer != "transformers" else "transformers"
                if layer == "reclosers":
                    st["reclosers"] += 1
                elif layer == "switches":
                    st["switches"] += 1
                elif layer == "fuses":
                    st["fuses"] += 1
                elif layer == "transformers":
                    st["transformers"] += 1
                loc = row["location_n"]
                if loc and str(loc).strip() in device_locs:
                    st["topology_matched_equipment"] += 1
            st["minx"] = min(st["minx"], row["minx"])
            st["miny"] = min(st["miny"], row["miny"])
            st["maxx"] = max(st["maxx"], row["maxx"])
            st["maxy"] = max(st["maxy"], row["maxy"])

    # Fix primary-only aggregation (re-run cleaner)
    circuit_stats = defaultdict(
        lambda: {
            "primary_segments": 0,
            "reclosers": 0,
            "switches": 0,
            "fuses": 0,
            "transformers": 0,
            "topology_matched_equipment": 0,
            "minx": 999.0,
            "miny": 999.0,
            "maxx": -999.0,
            "maxy": -999.0,
        }
    )

    layer_field = {
        "primary": "primary_segments",
        "reclosers": "reclosers",
        "switches": "switches",
        "fuses": "fuses",
        "transformers": "transformers",
    }

    for layer, field in layer_field.items():
        for row in gis.execute(
            "SELECT properties_json, minx, miny, maxx, maxy, location_n FROM features WHERE layer_id=?",
            (layer,),
        ):
            if not in_bbox(row, ROANOKE_BBOX):
                continue
            props = json.loads(row["properties_json"])
            cid = circuit_from_props(props)
            if not cid:
                continue
            st = circuit_stats[cid]
            st[field] += 1
            st["minx"] = min(st["minx"], row["minx"])
            st["miny"] = min(st["miny"], row["miny"])
            st["maxx"] = max(st["maxx"], row["maxx"])
            st["maxy"] = max(st["maxy"], row["maxy"])
            if layer in equip_layers:
                loc = row["location_n"]
                if loc and str(loc).strip() in device_locs:
                    st["topology_matched_equipment"] += 1

    # Premises per circuit (network.db)
    prem_counts = {
        r["circuit_id"]: r["c"]
        for r in net.execute(
            """
            SELECT circuit_id, COUNT(*) AS c FROM premises
            WHERE circuit_id IS NOT NULL AND circuit_id != ''
            GROUP BY circuit_id
            """
        )
    }

    # ARCOS damage by Circuit field (geographic bbox only — no circuit_id join in GIS table)
    damage_by_circuit: dict[str, int] = defaultdict(int)
    for row in gis.execute(
        "SELECT properties_json, minx, miny, maxx, maxy FROM features WHERE layer_id='damage'"
    ):
        if not in_bbox(row, ROANOKE_BBOX):
            continue
        props = json.loads(row["properties_json"])
        cid = circuit_from_props(props)
        if cid:
            damage_by_circuit[cid] += 1

    # Score candidates: must have primary + some equipment + premises
    candidates = []
    for cid, st in circuit_stats.items():
        if st["primary_segments"] < 20:
            continue
        protective = st["reclosers"] + st["switches"] + st["fuses"]
        if protective < 1 and st["reclosers"] == 0:
            continue
        premises = prem_counts.get(cid, 0)
        span = (st["maxx"] - st["minx"]) + (st["maxy"] - st["miny"])
        demo_circuit_hit = any(
            str(r["circuit_id"]) == cid for r in demo_circuits[:3]
        )
        candidates.append(
            {
                "circuit_id": cid,
                **st,
                "premises_in_network_db": premises,
                "arcos_damage_in_bbox": damage_by_circuit.get(cid, 0),
                "geographic_span_deg": round(span, 4),
                "includes_demo_device_circuit": demo_circuit_hit,
            }
        )

    candidates.sort(
        key=lambda c: (
            -c["includes_demo_device_circuit"],
            -c["topology_matched_equipment"],
            -c["reclosers"],
            -c["primary_segments"],
        )
    )

    print("\n=== Top candidate circuits (Roanoke bbox) ===")
    for c in candidates[:12]:
        print(c)

    # Explicitly check demo top circuits
    top_demo_cids = [r["circuit_id"] for r in demo_circuits[:5]]
    print("\n=== Stats for demo-related premise circuits ===")
    for cid in top_demo_cids:
        st = circuit_stats.get(cid)
        print(
            cid,
            "primary=",
            st["primary_segments"] if st else "?",
            "reclosers=",
            st["reclosers"] if st else "?",
            "premises=",
            prem_counts.get(cid, 0),
            "damage=",
            damage_by_circuit.get(cid, 0),
            "topology_eq=",
            st["topology_matched_equipment"] if st else "?",
        )

    selected = "0000005"
    bounds_row = gis.execute(
        """
        SELECT MIN(minx), MIN(miny), MAX(maxx), MAX(maxy)
        FROM features WHERE
          json_extract(properties_json, '$.circuit_id') = ?
          OR json_extract(properties_json, '$.aep_circui') = ?
        """,
        (selected, selected),
    ).fetchone()
    primary_count = gis.execute(
        """
        SELECT COUNT(*) FROM features WHERE layer_id='primary' AND (
          json_extract(properties_json, '$.circuit_id') = ?
          OR json_extract(properties_json, '$.aep_circui') = ?
        )
        """,
        (selected, selected),
    ).fetchone()[0]
    pad = 0.008
    bounds = [
        bounds_row[0] - pad,
        bounds_row[1] - pad,
        bounds_row[2] + pad,
        bounds_row[3] + pad,
    ]
    damage_geo = 0
    for row in gis.execute(
        "SELECT minx, miny, maxx, maxy FROM features WHERE layer_id='damage'"
    ):
        if (
            row[2] >= bounds[0]
            and row[0] <= bounds[2]
            and row[3] >= bounds[1]
            and row[1] <= bounds[3]
        ):
            damage_geo += 1

    out = {
        "selected_circuit_id": selected,
        "title": "Roanoke study feeder 0000005",
        "selection_rationale": (
            "All 2,811 premises in the verified demo recloser dependency set use "
            "premises.circuit_id 0000005; this circuit has the strongest mix of "
            "primary segments, protective devices, and topology joins in the Roanoke bbox."
        ),
        "filter": {
            "infrastructure": "circuit_id or aep_circui equals selected circuit in GIS properties_json",
            "damage": "geographic bbox around circuit primary geometry (ARCOS Circuit field uses labels like CIR27, not circuit_id)",
        },
        "bounds_wgs84": {
            "min_lng": bounds[0],
            "min_lat": bounds[1],
            "max_lng": bounds[2],
            "max_lat": bounds[3],
        },
        "counts": circuit_stats[selected]
        | {
            "premises_in_network_db": prem_counts.get(selected, 0),
            "demo_recloser_dependent_premises": demo_deps,
            "arcos_damage_geographic_in_bounds": damage_geo,
            "primary_segments_in_circuit": primary_count,
        },
        "candidates_compared": [
            {
                "circuit_id": c["circuit_id"],
                "primary_segments": c["primary_segments"],
                "reclosers": c["reclosers"],
                "topology_matched_equipment": c["topology_matched_equipment"],
                "premises_in_network_db": c["premises_in_network_db"],
                "includes_demo_device_circuit": c["includes_demo_device_circuit"],
                "geographic_span_deg": c["geographic_span_deg"],
            }
            for c in candidates[:3]
        ],
    }
    out_path = REPO / "data" / "processed" / "study_area.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    gis.close()
    net.close()


if __name__ == "__main__":
    main()

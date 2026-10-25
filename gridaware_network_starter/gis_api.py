"""Read-only GIS layer API. Does not modify network.db."""
from __future__ import annotations

import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

REPO_ROOT = Path(__file__).resolve().parents[1]
GIS_DB = Path(os.getenv("GIS_DB", str(REPO_ROOT / "data" / "processed" / "gis.db")))
JOIN_REPORT = REPO_ROOT / "data" / "processed" / "join_report.json"
STUDY_AREA_CANDIDATES = (
    REPO_ROOT / "data" / "processed" / "study_area.json",
    REPO_ROOT / "config" / "study_area.json",
)
DEMO_SECTION_CANDIDATES = (
    REPO_ROOT / "data" / "processed" / "demo_section.json",
    REPO_ROOT / "config" / "demo_section.json",
)
PROTECTIVE_LAYER_IDS = frozenset({"reclosers", "switches", "fuses"})
NETWORK_DB = Path(os.getenv("NETWORK_DB", str(Path(__file__).resolve().parent / "network.db")))

router = APIRouter(prefix="/gis", tags=["gis"])

MAX_FEATURES = 8000


def gis_connect() -> sqlite3.Connection:
    if not GIS_DB.exists():
        raise HTTPException(
            status_code=503,
            detail="GIS database not built. Run python scripts/build_gis_layers.py",
        )
    con = sqlite3.connect(f"file:{GIS_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def network_connect() -> sqlite3.Connection | None:
    if not NETWORK_DB.exists():
        return None
    con = sqlite3.connect(f"file:{NETWORK_DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@lru_cache(maxsize=1)
def matched_location_ids() -> frozenset[str]:
    net = network_connect()
    if net is None:
        return frozenset()
    try:
        rows = net.execute(
            "SELECT location_id FROM devices WHERE location_id IS NOT NULL"
        ).fetchall()
        return frozenset(str(r[0]).strip() for r in rows if r[0])
    finally:
        net.close()


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must be minLng,minLat,maxLng,maxLat")
    try:
        min_lng, min_lat, max_lng, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox values must be numbers") from exc
    return min_lng, min_lat, max_lng, max_lat


@router.get("/catalog")
def gis_catalog():
    with gis_connect() as con:
        layers = [dict(r) for r in con.execute("SELECT * FROM layers")]
    for layer in layers:
        layer["default_on"] = bool(layer["default_on"])
        layer["bbox_required"] = bool(layer["bbox_required"])
        layer["fields"] = json.loads(layer.pop("fields_json"))
    join = None
    if JOIN_REPORT.exists():
        join = json.loads(JOIN_REPORT.read_text(encoding="utf-8"))
    return {"layers": layers, "join": join, "note": "GIS geometry is independent of confirmed outages."}


@lru_cache(maxsize=1)
def load_study_area() -> dict | None:
    for path in STUDY_AREA_CANDIDATES:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


@lru_cache(maxsize=1)
def load_demo_section() -> dict | None:
    for path in DEMO_SECTION_CANDIDATES:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def demo_section_bounds(section: dict) -> tuple[float, float, float, float] | None:
    b = section.get("bounds_wgs84")
    if not b:
        return None
    return b["min_lng"], b["min_lat"], b["max_lng"], b["max_lat"]


def demo_protective_allowlist(section: dict) -> dict[str, frozenset[str]]:
    """layer_id -> allowed location_n values for demo section."""
    by_layer: dict[str, set[str]] = {}
    for dev in section.get("protective_devices") or []:
        layer = dev.get("layer")
        loc = dev.get("location_n")
        if not layer or not loc:
            continue
        by_layer.setdefault(str(layer), set()).add(str(loc).strip())
    return {layer: frozenset(locs) for layer, locs in by_layer.items()}


def _circuit_property_clause(circuit: str) -> tuple[str, list]:
    return (
        " AND (json_extract(properties_json, '$.circuit_id') = ?"
        " OR json_extract(properties_json, '$.aep_circui') = ?)",
        [circuit, circuit],
    )


@router.get("/study-area")
def gis_study_area():
    """Default demo study circuit metadata (from scripts/analyze_study_areas.py)."""
    area = load_study_area()
    if area is None:
        raise HTTPException(
            status_code=404,
            detail="Study area not configured. Run python scripts/analyze_study_areas.py",
        )
    return area


@router.get("/demo-section")
def gis_demo_section():
    """Compact demo map section (protective allowlist + geographic bounds)."""
    section = load_demo_section()
    if section is None:
        raise HTTPException(
            status_code=404,
            detail="Demo section not configured. Run python scripts/finalize_demo_section.py",
        )
    return section


@router.get("/join-stats")
def gis_join_stats():
    if not JOIN_REPORT.exists():
        raise HTTPException(status_code=404, detail="Join report not found. Rebuild GIS layers.")
    return json.loads(JOIN_REPORT.read_text(encoding="utf-8"))


@router.get("/features")
def gis_features(
    layer: str = Query(..., min_length=2),
    bbox: str | None = None,
    zoom: float | None = None,
    limit: int = 4000,
    circuit: str | None = Query(
        None,
        description="Filter by GIS circuit_id / aep_circui. Damage uses geographic study bounds instead.",
    ),
    demo_section: bool = Query(
        False,
        description="When true, restrict to compact demo section (allowlisted devices + bbox primary).",
    ),
):
    box = parse_bbox(bbox)
    cap = min(max(limit, 1), MAX_FEATURES)
    matched = matched_location_ids()
    study = load_study_area()
    section = load_demo_section() if demo_section else None
    filter_note: str | None = None

    with gis_connect() as con:
        meta = con.execute("SELECT * FROM layers WHERE layer_id=?", (layer,)).fetchone()
        if not meta:
            raise HTTPException(status_code=404, detail="Unknown GIS layer")
        if zoom is not None and zoom < meta["min_zoom"]:
            return {
                "type": "FeatureCollection",
                "features": [],
                "layer": layer,
                "returned": 0,
                "truncated": False,
                "reason": f"Zoom {zoom:.1f} is below layer minimum {meta['min_zoom']}",
            }
        if section and layer == "damage":
            return {
                "type": "FeatureCollection",
                "features": [],
                "layer": layer,
                "returned": 0,
                "truncated": False,
                "filter_note": "Historical damage hidden in demo section mode",
            }
        sql = "SELECT feature_id, location_n, properties_json, geometry_json FROM features WHERE layer_id=?"
        params: list = [layer]
        allowlist: frozenset[str] | None = None
        if section:
            section_box = demo_section_bounds(section)
            if section_box:
                box = section_box
            allow_by_layer = demo_protective_allowlist(section)
            if layer in PROTECTIVE_LAYER_IDS:
                allowlist = allow_by_layer.get(layer, frozenset())
                if not allowlist:
                    return {
                        "type": "FeatureCollection",
                        "features": [],
                        "layer": layer,
                        "returned": 0,
                        "truncated": False,
                        "filter_note": f"No demo-section devices on layer {layer}",
                    }
                placeholders = ",".join("?" for _ in allowlist)
                sql += f" AND location_n IN ({placeholders})"
                params.extend(sorted(allowlist))
                filter_note = (
                    "Demo section: topology-validated protective device allowlist"
                )
            elif layer == "primary":
                pgis = section.get("primary_gis_circuit_id")
                if pgis:
                    clause, clause_params = _circuit_property_clause(str(pgis).strip())
                    sql += clause
                    params.extend(clause_params)
                    filter_note = (
                        "Demo section: local GIS primary by circuit_id "
                        f"{pgis} within bounds (geographic context; not network topology proof)"
                    )
                else:
                    filter_note = (
                        "Demo section: no primary_gis_circuit_id configured; bbox only"
                    )
            elif layer in ("transformers", "secondary", "poles", "emergency"):
                return {
                    "type": "FeatureCollection",
                    "features": [],
                    "layer": layer,
                    "returned": 0,
                    "truncated": False,
                    "filter_note": f"Layer {layer} omitted from demo section view",
                }
        elif circuit and layer != "damage":
            clause, clause_params = _circuit_property_clause(circuit.strip())
            sql += clause
            params.extend(clause_params)
            filter_note = (
                f"Infrastructure filtered by circuit_id/aep_circui={circuit.strip()}"
            )
        elif circuit and layer == "damage":
            if study and study.get("bounds_wgs84"):
                b = study["bounds_wgs84"]
                box = (b["min_lng"], b["min_lat"], b["max_lng"], b["max_lat"])
                filter_note = (
                    "Damage filtered by geographic bbox around study circuit "
                    "(ARCOS Circuit labels are not circuit_id)"
                )
            else:
                filter_note = "Damage layer ignores circuit filter without study bounds"
        if box:
            min_lng, min_lat, max_lng, max_lat = box
            sql += " AND maxx>=? AND minx<=? AND maxy>=? AND miny<=?"
            params.extend([min_lng, max_lng, min_lat, max_lat])
        elif meta["bbox_required"] and not circuit and not section:
            return {
                "type": "FeatureCollection",
                "features": [],
                "layer": layer,
                "returned": 0,
                "truncated": False,
                "reason": "This layer requires a map bbox to avoid loading the full dataset.",
            }
        sql += " LIMIT ?"
        params.append(cap + 1)
        rows = con.execute(sql, params).fetchall()

    truncated = len(rows) > cap
    rows = rows[:cap]
    features = []
    for row in rows:
        props = json.loads(row["properties_json"])
        loc = row["location_n"]
        props["_layer"] = layer
        props["_feature_id"] = row["feature_id"]
        props["_location_n"] = loc
        props["_topology_match"] = bool(loc and loc in matched)
        features.append(
            {
                "type": "Feature",
                "id": f"{layer}:{row['feature_id']}",
                "geometry": json.loads(row["geometry_json"]),
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "layer": layer,
        "returned": len(features),
        "truncated": truncated,
        "filter_note": filter_note,
    }


@router.get("/location/{location_id}")
def gis_location(location_id: str):
    loc = location_id.strip()
    if not loc:
        raise HTTPException(status_code=400, detail="location_id required")

    assets = []
    with gis_connect() as con:
        for row in con.execute(
            "SELECT layer_id, feature_id, location_n, properties_json FROM features WHERE location_n=?",
            (loc,),
        ):
            assets.append(
                {
                    "layer_id": row["layer_id"],
                    "feature_id": row["feature_id"],
                    "location_n": row["location_n"],
                    "properties": json.loads(row["properties_json"]),
                }
            )

    devices = []
    net = network_connect()
    if net is not None:
        try:
            for row in net.execute(
                """
                SELECT d.device_key, d.device_type, d.location_id, d.source_type, d.source_id,
                       COUNT(dp.premise_id) AS dependent_premises
                FROM devices d
                LEFT JOIN dependencies dp ON d.device_key = dp.device_key
                WHERE d.location_id = ?
                GROUP BY d.device_key
                """,
                (loc,),
            ):
                devices.append(dict(row))
        finally:
            net.close()

    return {
        "location_id": loc,
        "match_method": "exact location_n = devices.location_id",
        "gis_assets": assets,
        "devices": devices,
        "note": (
            "A GIS location match is an identifier join only. It does not confirm an outage "
            "or electrical switching state."
        ),
    }

"""Convert AEP shapefiles into WGS84 GIS features for the operations map.

Reads extracted shapefiles under data/raw/shapefiles/ and writes:
  data/processed/gis.db
  data/processed/catalog.json
  data/processed/join_report.json

Does not modify network.db. Join statistics are read-only.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path

import shapefile

REPO = Path(__file__).resolve().parents[1]
SHAPE_ROOT = REPO / "data" / "raw" / "shapefiles"
PROCESSED = REPO / "data" / "processed"
NETWORK_DB = REPO / "gridaware_network_starter" / "network.db"

# Web Mercator (EPSG:3857) radius used by the emergency-facility shapefiles.
WEB_MERCATOR_R = 6378137.0

LAYER_SPECS = [
    {
        "id": "primary",
        "title": "Primary electrical lines",
        "path": SHAPE_ROOT / "Data1" / "Primary_ExportFeatures.shp",
        "geometry": "line",
        "default_on": True,
        "min_zoom": 11,
        "bbox_required": True,
        "keep": [
            "id",
            "location_n",
            "location_1",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "status",
            "usage",
            "mounting",
            "nominal_vo",
            "existing_p",
            "eo_source_",
            "owner_name",
            "network_ty",
            "aep_constr",
        ],
    },
    {
        "id": "secondary",
        "title": "Secondary electrical lines",
        "path": SHAPE_ROOT / "Data2" / "Secondary_ExportFeatures.shp",
        "geometry": "line",
        "default_on": False,
        "min_zoom": 13,
        "bbox_required": True,
        "keep": [
            "id",
            "location_n",
            "location_1",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "status",
            "usage",
            "mounting",
            "nominal_vo",
            "existing_p",
            "eo_source_",
            "owner_name",
            "network_ty",
        ],
    },
    {
        "id": "poles",
        "title": "Poles",
        "path": SHAPE_ROOT / "Data1" / "Pole_Clip.shp",
        "geometry": "point",
        "default_on": False,
        "min_zoom": 13,
        "bbox_required": True,
        "keep": [
            "id",
            "location_n",
            "status",
            "usage",
            "material",
            "height",
            "class",
            "owner_name",
            "eo_source_",
            "number",
        ],
    },
    {
        "id": "transformers",
        "title": "Transformers",
        "path": SHAPE_ROOT / "Data2" / "Transformer_Clip.shp",
        "geometry": "point",
        "default_on": False,
        "min_zoom": 12,
        "bbox_required": True,
        "keep": [
            "id",
            "location_n",
            "device_typ",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "status",
            "mounting",
            "source_nom",
            "load_nomin",
            "aep_custom",
            "eo_source_",
            "bank_confi",
            "upstream_l",
        ],
    },
    {
        "id": "fuses",
        "title": "Fuses",
        "path": SHAPE_ROOT / "Data1" / "Fuse_Bank_Clip.shp",
        "geometry": "point",
        "default_on": False,
        "min_zoom": 11,
        "bbox_required": False,
        "keep": [
            "id",
            "location_n",
            "device_typ",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "normal_sta",
            "status",
            "mounting",
            "nominal_vo",
            "aep_custom",
            "eo_source_",
            "upstream_l",
            "scada_cont",
        ],
    },
    {
        "id": "reclosers",
        "title": "Reclosers",
        "path": SHAPE_ROOT / "Data2" / "Recloser_Bank_Clip.shp",
        "geometry": "point",
        "default_on": True,
        "min_zoom": 0,
        "bbox_required": False,
        "keep": [
            "id",
            "location_n",
            "device_typ",
            "type",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "normal_sta",
            "status",
            "nominal_vo",
            "aep_custom",
            "eo_source_",
            "scada_cont",
            "upstream_l",
        ],
    },
    {
        "id": "switches",
        "title": "Switches",
        "path": SHAPE_ROOT / "Data2" / "Switch_Clip.shp",
        "geometry": "point",
        "default_on": False,
        "min_zoom": 11,
        "bbox_required": False,
        "keep": [
            "id",
            "location_n",
            "device_typ",
            "circuit_id",
            "aep_circui",
            "aep_statio",
            "normal_sta",
            "status",
            "mounting",
            "nominal_vo",
            "aep_custom",
            "eo_source_",
            "scada_cont",
            "upstream_l",
        ],
    },
    {
        "id": "damage",
        "title": "Historical ARCOS damage",
        "path": SHAPE_ROOT / "Data1" / "arcos_prod_damage_09_28_Clip.shp",
        "geometry": "point",
        "default_on": True,
        "min_zoom": 0,
        "bbox_required": False,
        "keep": [
            "Outage_Num",
            "Incident_W",
            "Event",
            "Region",
            "District",
            "Crew_Area",
            "Substation",
            "Circuit",
            "Report_Tim",
            "Status",
            "Repaired",
            "Repaired_D",
            "Repaired_B",
            "Asset_Type",
            "Inform_Wor",
            "Longitude",
            "Latitude",
            "Access_Iss",
            "Special_Eq",
            "NEAR_FID",
            "NEAR_DIST",
        ],
    },
    {
        "id": "emergency",
        "title": "Emergency facilities",
        "paths": [
            (SHAPE_ROOT / "Data1" / "Ambulance_Servi_Pairwis_Clip.shp", "ambulance"),
            (SHAPE_ROOT / "Data1" / "Fire_Stations_E_Pairwis_Clip.shp", "fire_station"),
            (SHAPE_ROOT / "Data1" / "Hospitals_Medic_Pairwis_Clip.shp", "hospital"),
        ],
        "geometry": "point",
        "default_on": False,
        "min_zoom": 0,
        "bbox_required": False,
        "keep": [
            "NAME",
            "ADDRESS",
            "CITY",
            "STATE",
            "ZIPCODE",
            "FCODE",
            "FTYPE",
            "GNIS_ID",
            "PERMANENT_",
            "facility_kind",
        ],
    },
]


def json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    lng = (x / WEB_MERCATOR_R) * 180.0 / math.pi
    lat = (2.0 * math.atan(math.exp(y / WEB_MERCATOR_R)) - math.pi / 2.0) * 180.0 / math.pi
    return lng, lat


def read_crs(shp_path: Path) -> str:
    prj = shp_path.with_suffix(".prj")
    if not prj.exists():
        return "unknown"
    text = prj.read_text(encoding="utf-8", errors="replace")
    if "Web_Mercator" in text or "Mercator_Auxiliary_Sphere" in text:
        return "EPSG:3857"
    if "GCS_WGS_1984" in text or "WGS_1984" in text:
        return "EPSG:4326"
    return text[:160]


def convert_points(points, source_crs: str) -> list[list[float]]:
    out = []
    for pt in points:
        x, y = float(pt[0]), float(pt[1])
        if source_crs == "EPSG:3857":
            x, y = mercator_to_wgs84(x, y)
        out.append([x, y])
    return out


def shape_to_geojson(shape, source_crs: str):
    pts = convert_points(shape.points, source_crs)
    if not pts:
        return None
    # pyshp: POINT / POINTZ / POLYLINE / POLYLINEZ
    if shape.shapeType in (1, 11, 21):
        return {"type": "Point", "coordinates": pts[0]}
    if shape.shapeType in (3, 13, 23):
        parts = list(shape.parts) + [len(pts)]
        rings = [pts[parts[i] : parts[i + 1]] for i in range(len(parts) - 1)]
        rings = [r for r in rings if len(r) >= 2]
        if not rings:
            return None
        if len(rings) == 1:
            return {"type": "LineString", "coordinates": rings[0]}
        return {"type": "MultiLineString", "coordinates": rings}
    # Fallback: treat as point from first vertex
    return {"type": "Point", "coordinates": pts[0]}


def geom_bbox(geom) -> tuple[float, float, float, float] | None:
    coords: list[list[float]] = []

    def walk(node):
        if not node:
            return
        if isinstance(node[0], (int, float)):
            coords.append(node)  # type: ignore[arg-type]
            return
        for child in node:
            walk(child)

    walk(geom.get("coordinates"))
    if not coords:
        return None
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return min(xs), min(ys), max(xs), max(ys)


def pick_props(record_map: dict, keep: list[str], extra: dict | None = None) -> dict:
    props = {}
    for key in keep:
        if key in record_map:
            props[key] = json_safe(record_map[key])
    if extra:
        props.update(extra)
    return props


def load_layer_shapefile(shp_path: Path, spec: dict, facility_kind: str | None = None):
    if not shp_path.exists():
        raise FileNotFoundError(shp_path)
    source_crs = read_crs(shp_path)
    reader = shapefile.Reader(str(shp_path))
    names = [f[0] for f in reader.fields[1:]]
    rows = []
    for sr in reader.iterShapeRecords():
        rec = {names[i]: sr.record[i] for i in range(len(names))}
        geom = shape_to_geojson(sr.shape, source_crs)
        if geom is None:
            continue
        extra = {"facility_kind": facility_kind} if facility_kind else None
        props = pick_props(rec, spec["keep"], extra)
        feature_id = (
            rec.get("id")
            or rec.get("PERMANENT_")
            or rec.get("global_id")
            or rec.get("Outage_Num")
        )
        location_n = rec.get("location_n") or rec.get("location_1")
        if location_n is not None:
            location_n = str(location_n).strip() or None
        bbox = geom_bbox(geom)
        if bbox is None:
            continue
        rows.append(
            {
                "feature_id": str(feature_id) if feature_id is not None else None,
                "location_n": location_n,
                "properties": props,
                "geometry": geom,
                "bbox": bbox,
                "source_crs": source_crs,
            }
        )
    reader.close()
    return rows, source_crs, names


def create_gis_db(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.executescript(
        """
        CREATE TABLE layers (
            layer_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            geometry TEXT NOT NULL,
            source_file TEXT,
            source_crs TEXT,
            record_count INTEGER,
            default_on INTEGER,
            min_zoom INTEGER,
            bbox_required INTEGER,
            fields_json TEXT
        );
        CREATE TABLE features (
            layer_id TEXT NOT NULL,
            feature_id TEXT NOT NULL,
            location_n TEXT,
            minx REAL, miny REAL, maxx REAL, maxy REAL,
            properties_json TEXT NOT NULL,
            geometry_json TEXT NOT NULL,
            PRIMARY KEY (layer_id, feature_id)
        );
        CREATE INDEX idx_features_layer_bbox ON features(layer_id, minx, maxx, miny, maxy);
        CREATE INDEX idx_features_location ON features(location_n);
        """
    )
    return con


def write_join_report(con: sqlite3.Connection) -> dict:
    report: dict = {
        "method": "Exact string match of GIS features.location_n to network.db devices.location_id. No proximity matching.",
        "network_db": str(NETWORK_DB) if NETWORK_DB.exists() else None,
        "layers": {},
        "totals": {},
    }
    if not NETWORK_DB.exists():
        report["warning"] = "network.db not found; join validation skipped"
        return report

    net = sqlite3.connect(NETWORK_DB)
    device_locations = {
        str(row[0]).strip()
        for row in net.execute("SELECT location_id FROM devices WHERE location_id IS NOT NULL")
        if row[0]
    }
    devices_by_location: dict[str, list[tuple[str, str]]] = {}
    for key, dtype, loc in net.execute(
        "SELECT device_key, device_type, location_id FROM devices WHERE location_id IS NOT NULL"
    ):
        loc = str(loc).strip()
        devices_by_location.setdefault(loc, []).append((key, dtype))

    total_gis_with_loc = 0
    total_matched_features = 0
    matched_location_ids = set()
    unmatched_demo = None

    for layer_id, in con.execute("SELECT layer_id FROM layers"):
        locs = [
            row[0]
            for row in con.execute(
                "SELECT DISTINCT location_n FROM features WHERE layer_id=? AND location_n IS NOT NULL AND location_n != ''",
                (layer_id,),
            )
        ]
        feature_count = con.execute(
            "SELECT COUNT(*) FROM features WHERE layer_id=?", (layer_id,)
        ).fetchone()[0]
        with_loc = con.execute(
            "SELECT COUNT(*) FROM features WHERE layer_id=? AND location_n IS NOT NULL AND location_n != ''",
            (layer_id,),
        ).fetchone()[0]
        matched_locs = [loc for loc in locs if loc in device_locations]
        matched_feat_set = set(matched_locs)
        matched_feats = 0
        if matched_feat_set:
            for (loc,) in con.execute(
                "SELECT location_n FROM features WHERE layer_id=? AND location_n IS NOT NULL",
                (layer_id,),
            ):
                if loc in matched_feat_set:
                    matched_feats += 1
        total_gis_with_loc += with_loc
        total_matched_features += matched_feats
        matched_location_ids.update(matched_locs)
        report["layers"][layer_id] = {
            "features": feature_count,
            "features_with_location_n": with_loc,
            "distinct_location_n": len(locs),
            "distinct_location_n_matched_to_devices": len(matched_locs),
            "features_with_matched_location_n": matched_feats,
        }

    demo_key = "eo_isolating_eqpt_inst*321305938"
    demo = net.execute(
        "SELECT device_key, device_type, location_id FROM devices WHERE device_key=?",
        (demo_key,),
    ).fetchone()
    if demo:
        loc = demo[2]
        gis_hits = list(
            con.execute(
                "SELECT layer_id, feature_id, location_n FROM features WHERE location_n=?",
                (loc,),
            )
        )
        unmatched_demo = {
            "device_key": demo[0],
            "device_type": demo[1],
            "location_id": loc,
            "gis_feature_matches": [
                {"layer_id": r[0], "feature_id": r[1], "location_n": r[2]} for r in gis_hits
            ],
        }

    report["totals"] = {
        "devices_in_network_db": net.execute("SELECT COUNT(*) FROM devices").fetchone()[0],
        "distinct_device_location_id": len(device_locations),
        "gis_features_with_location_n": total_gis_with_loc,
        "gis_features_matched_exact_location_id": total_matched_features,
        "distinct_matched_location_ids": len(matched_location_ids),
    }
    report["demo_recloser"] = unmatched_demo
    net.close()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=PROCESSED / "gis.db")
    args = parser.parse_args()

    missing = [
        spec["path"]
        for spec in LAYER_SPECS
        if spec.get("path") and not spec["path"].exists()
    ]
    for spec in LAYER_SPECS:
        for path, _kind in spec.get("paths", []):
            if not path.exists():
                missing.append(path)
    if missing:
        raise SystemExit(
            "Missing shapefiles. Extract Data1.zip and Data2.zip first:\n"
            + "\n".join(str(p) for p in missing)
        )

    con = create_gis_db(args.out)
    catalog_layers = []

    for spec in LAYER_SPECS:
        layer_id = spec["id"]
        print(f"Processing {layer_id}...")
        all_rows = []
        source_files = []
        source_crs_set = set()
        field_names: list[str] = []

        if "paths" in spec:
            for path, kind in spec["paths"]:
                rows, crs, names = load_layer_shapefile(path, spec, kind)
                all_rows.extend(rows)
                source_files.append(path.name)
                source_crs_set.add(crs)
                field_names = names
        else:
            rows, crs, names = load_layer_shapefile(spec["path"], spec)
            all_rows.extend(rows)
            source_files.append(spec["path"].name)
            source_crs_set.add(crs)
            field_names = names

        used_ids: dict[str, int] = {}
        batch = []
        for row in all_rows:
            fid = row["feature_id"] or "unknown"
            if fid in used_ids:
                used_ids[fid] += 1
                fid = f"{fid}:{used_ids[fid]}"
            else:
                used_ids[fid] = 0
            minx, miny, maxx, maxy = row["bbox"]
            batch.append(
                (
                    layer_id,
                    fid,
                    row["location_n"],
                    minx,
                    miny,
                    maxx,
                    maxy,
                    json.dumps(row["properties"], separators=(",", ":")),
                    json.dumps(row["geometry"], separators=(",", ":")),
                )
            )
        con.executemany(
            """INSERT INTO features
               (layer_id, feature_id, location_n, minx, miny, maxx, maxy, properties_json, geometry_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            batch,
        )
        source_crs = ",".join(sorted(source_crs_set))
        con.execute(
            """INSERT INTO layers VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                layer_id,
                spec["title"],
                spec["geometry"],
                ";".join(source_files),
                source_crs,
                len(batch),
                1 if spec["default_on"] else 0,
                spec["min_zoom"],
                1 if spec["bbox_required"] else 0,
                json.dumps(spec["keep"]),
            ),
        )
        catalog_layers.append(
            {
                "id": layer_id,
                "title": spec["title"],
                "geometry": spec["geometry"],
                "source_file": ";".join(source_files),
                "source_crs": source_crs,
                "record_count": len(batch),
                "default_on": spec["default_on"],
                "min_zoom": spec["min_zoom"],
                "bbox_required": spec["bbox_required"],
                "fields": spec["keep"],
                "source_field_names": field_names,
            }
        )
        print(f"  {len(batch):,} features  CRS={source_crs}")

    con.commit()
    join_report = write_join_report(con)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / "catalog.json").write_text(
        json.dumps({"layers": catalog_layers}, indent=2), encoding="utf-8"
    )
    (PROCESSED / "join_report.json").write_text(
        json.dumps(join_report, indent=2), encoding="utf-8"
    )
    con.close()
    print("Wrote", args.out)
    print("Join totals:", json.dumps(join_report.get("totals"), indent=2))
    if join_report.get("demo_recloser"):
        print("Demo recloser GIS matches:", join_report["demo_recloser"])


if __name__ == "__main__":
    main()

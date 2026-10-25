"""Validate one premise→transformer→recloser chain from real records (read-only)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NET = REPO / "gridaware_network_starter" / "network.db"
GIS = REPO / "data" / "processed" / "gis.db"
DEMO_LOC = "37800281C36078"
DEMO_KEY = "eo_isolating_eqpt_inst*321305938"

FIELDS_OF_INTEREST = (
    "location_n",
    "location_1",
    "circuit_id",
    "aep_circui",
    "upstream_l",
    "normal_sta",
    "aep_statio",
    "network_ty",
)


def gis_by_location(con: sqlite3.Connection, loc: str) -> list[dict]:
    rows = []
    for r in con.execute(
        "SELECT layer_id, feature_id, location_n, properties_json FROM features WHERE location_n=?",
        (loc,),
    ):
        props = json.loads(r["properties_json"])
        rows.append(
            {
                "layer_id": r["layer_id"],
                "feature_id": r["feature_id"],
                "location_n": r["location_n"],
                "fields": {k: props.get(k) for k in FIELDS_OF_INTEREST if k in props},
            }
        )
    return rows


def main() -> None:
    net = sqlite3.connect(NET)
    net.row_factory = sqlite3.Row
    gis = sqlite3.connect(GIS)
    gis.row_factory = sqlite3.Row

    print("=== Demo recloser in network.db ===")
    dev = net.execute(
        "SELECT * FROM devices WHERE device_key=?", (DEMO_KEY,)
    ).fetchone()
    print(dict(dev))

    print("\n=== GIS assets at demo recloser location_n ===")
    for row in gis_by_location(gis, DEMO_LOC):
        print(row)

    print("\n=== Find transformer device keys that share premises with demo recloser ===")
    # Devices on same premises as demo (sample transformer types)
    transformer_keys = net.execute(
        """
        SELECT d.device_key, d.device_type, d.location_id, COUNT(*) AS shared
        FROM dependencies d1
        JOIN dependencies d2 ON d1.premise_id = d2.premise_id
        JOIN devices d ON d.device_key = d2.device_key
        WHERE d1.device_key = ?
          AND d.device_type LIKE '%Transformer%'
        GROUP BY d.device_key
        ORDER BY shared DESC
        LIMIT 5
        """,
        (DEMO_KEY,),
    ).fetchall()
    for r in transformer_keys:
        print(dict(r))

    if not transformer_keys:
        print("No Transformer device_type in upstream index for shared premises")
        # try any non-recloser device with high overlap
        alt = net.execute(
            """
            SELECT d.device_key, d.device_type, d.location_id, COUNT(*) AS shared
            FROM dependencies d1
            JOIN dependencies d2 ON d1.premise_id = d2.premise_id
            JOIN devices d ON d.device_key = d2.device_key
            WHERE d1.device_key = ?
            GROUP BY d.device_key
            ORDER BY shared DESC
            LIMIT 15
            """,
            (DEMO_KEY,),
        ).fetchall()
        print("\nTop co-listed upstream devices for demo recloser premises:")
        for r in alt:
            print(dict(r))

    xfm_key = transformer_keys[0]["device_key"] if transformer_keys else None
    xfm_loc = transformer_keys[0]["location_id"] if transformer_keys else None

    print("\n=== Pick one premise depending on BOTH demo recloser and a transformer (if any) ===")
    premise = None
    if xfm_key:
        premise = net.execute(
            """
            SELECT d1.premise_id FROM dependencies d1
            JOIN dependencies d2 ON d1.premise_id = d2.premise_id
            WHERE d1.device_key=? AND d2.device_key=?
            LIMIT 1
            """,
            (DEMO_KEY, xfm_key),
        ).fetchone()
    if not premise:
        premise = net.execute(
            "SELECT premise_id FROM dependencies WHERE device_key=? LIMIT 1",
            (DEMO_KEY,),
        ).fetchone()
    pid = premise[0]
    print("premise_id", pid)
    prem = net.execute("SELECT * FROM premises WHERE premise_id=?", (pid,)).fetchone()
    print("premises row", dict(prem))

    print("\n=== All upstream devices for this premise (network.db index) ===")
    upstream = net.execute(
        """
        SELECT d.device_key, d.device_type, d.location_id
        FROM dependencies dp
        JOIN devices d ON d.device_key = dp.device_key
        WHERE dp.premise_id=?
        ORDER BY d.device_type, d.device_key
        """,
        (pid,),
    ).fetchall()
    for u in upstream:
        print(dict(u))

    print("\n=== Customer GIS (Customer_Clip fields via gis.db if present) ===")
    # customers may not be in gis.db - check
    cust = gis.execute(
        "SELECT layer_id, properties_json FROM features WHERE layer_id LIKE '%customer%' LIMIT 1"
    ).fetchone()
    if cust:
        print("customer layer", cust[0])
    else:
        print("No customer layer in gis.db (expected — customers in network.db from shapefile import only)")

    print("\n=== Transformer GIS at transformer location_id (if found) ===")
    if xfm_loc:
        for row in gis_by_location(gis, str(xfm_loc).strip()):
            print(row)

    print("\n=== Primary segments near demo recloser: circuit_id / aep_circui sample ===")
    for r in gis.execute(
        """
        SELECT properties_json, minx, miny, maxx, maxy FROM features
        WHERE layer_id='primary'
          AND maxx >= -79.80 AND minx <= -79.78
          AND maxy >= 37.26 AND miny <= 37.28
        LIMIT 5
        """
    ):
        p = json.loads(r["properties_json"])
        print(
            {
                "circuit_id": p.get("circuit_id"),
                "aep_circui": p.get("aep_circui"),
                "location_n": p.get("location_n"),
                "upstream_l": p.get("upstream_l"),
                "normal_sta": p.get("normal_sta"),
            }
        )

    print("\n=== Recloser GIS fields (all keys sample) ===")
    rrow = gis.execute(
        "SELECT properties_json FROM features WHERE layer_id='reclosers' AND location_n=? LIMIT 1",
        (DEMO_LOC,),
    ).fetchone()
    if rrow:
        props = json.loads(rrow[0])
        for k in sorted(props.keys()):
            if any(x in k.lower() for x in ("circ", "upstr", "norm", "loc", "stat")):
                print(f"  {k}: {props[k]}")

    print("\n=== Primary labeled 0000005 near demo? (count in 0.02deg) ===")
    c5 = 0
    c6 = 0
    for r in gis.execute(
        "SELECT properties_json FROM features WHERE layer_id='primary'"
    ):
        p = json.loads(r[0])
        cid = str(p.get("circuit_id") or "").strip()
        if cid == "0000005":
            c5 += 1
        if cid == "0000006":
            c6 += 1
    print("total primary c5", c5, "c6", c6)

    gis.close()
    net.close()


if __name__ == "__main__":
    main()

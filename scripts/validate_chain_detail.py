"""Detail for premise 000052580 chain validation."""
import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NET = REPO / "gridaware_network_starter" / "network.db"
GIS = REPO / "data" / "processed" / "gis.db"
PID = "000052580"
XFRM_LOC = "37800259000284"
XFRM_KEY = "eo_power_xfrmr_inst*144043179"
RECL_LOC = "37800281C36078"
RECL_KEY = "eo_isolating_eqpt_inst*321305938"


def dump_loc(gis, loc):
    print(f"\n--- GIS location_n={loc} ---")
    for r in gis.execute(
        "SELECT layer_id, properties_json FROM features WHERE location_n=? ORDER BY layer_id",
        (loc,),
    ):
        p = json.loads(r["properties_json"])
        print(r["layer_id"], {k: p.get(k) for k in (
            "circuit_id", "aep_circui", "upstream_l", "normal_sta",
            "location_n", "location_1", "network_ty", "aep_statio",
        )})


def main():
    net = sqlite3.connect(NET)
    net.row_factory = sqlite3.Row
    gis = sqlite3.connect(GIS)
    gis.row_factory = sqlite3.Row

    print("Premise", PID, dict(net.execute("SELECT * FROM premises WHERE premise_id=?", (PID,)).fetchone()))
    print("\nUpstream devices (index membership only):")
    for r in net.execute(
        """
        SELECT d.device_key, d.device_type, d.location_id
        FROM dependencies dp JOIN devices d ON d.device_key=dp.device_key
        WHERE dp.premise_id=? ORDER BY d.device_type
        """,
        (PID,),
    ):
        print(" ", dict(r))

    dump_loc(gis, XFRM_LOC)
    dump_loc(gis, RECL_LOC)

    # Customer shapefile field via pyshp if available
    shp = REPO / "data" / "raw" / "shapefiles" / "Data1" / "Customer_Clip.shp"
    if shp.exists():
        import shapefile
        r = shapefile.Reader(str(shp))
        names = [f[0] for f in r.fields[1:]]
        idx = names.index("premise_nu") if "premise_nu" in names else None
        circ = names.index("circuit_id") if "circuit_id" in names else None
        for sr in r.iterShapeRecords():
            if idx is not None and str(sr.record[idx]).strip() == PID:
                rec = {names[i]: sr.record[i] for i in range(len(names))}
                print("\nCustomer_Clip record for premise", PID)
                for k in sorted(rec.keys()):
                    if rec[k] not in (None, "", " "):
                        print(f"  {k}: {rec[k]}")
                break

    # Can we link transformer to recloser via GIS upstream_l / location_1?
    print("\n=== Searching GIS text refs between xfrm and recloser locs ===")
    for layer in ("primary", "secondary", "transformers"):
        for r in gis.execute(
            "SELECT properties_json FROM features WHERE layer_id=?", (layer,)
        ):
            p = json.loads(r[0])
            loc = str(p.get("location_n") or "")
            u = str(p.get("upstream_l") or "")
            l1 = str(p.get("location_1") or "")
            if XFRM_LOC in (loc, u, l1) or RECL_LOC in (loc, u, l1):
                if u or l1:
                    print(layer, loc, "upstream_l", u, "location_1", l1, "circuit", p.get("circuit_id"), p.get("aep_circui"))

    net.close()
    gis.close()


if __name__ == "__main__":
    main()

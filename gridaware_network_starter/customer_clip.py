"""Read-only Customer_Clip attributes by premise_nu (when shapefile is present)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHP = REPO_ROOT / "data" / "raw" / "shapefiles" / "Data1" / "Customer_Clip.shp"

CUSTOMER_FIELDS = (
    "premise_nu",
    "circuit_id",
    "aep_xfmr_l",
    "aep_locati",
    "kind_of_se",
    "city",
    "state",
    "service_po",
    "service__1",
)


def customer_shp_path() -> Path:
    return Path(os.getenv("CUSTOMER_CLIP_SHP", str(DEFAULT_SHP)))


@lru_cache(maxsize=1)
def _index_by_premise() -> dict[str, dict] | None:
    shp = customer_shp_path()
    if not shp.exists():
        return None
    import shapefile

    reader = shapefile.Reader(str(shp))
    names = [f[0] for f in reader.fields[1:]]
    prem_idx = names.index("premise_nu")
    out: dict[str, dict] = {}
    for sr in reader.iterShapeRecords():
        pid = str(sr.record[prem_idx]).strip()
        if not pid:
            continue
        row = {names[i]: sr.record[i] for i in range(len(names))}
        out[pid] = row
    return out


def lookup_customer_clip(premise_id: str) -> dict | None:
    index = _index_by_premise()
    if index is None:
        return None
    row = index.get(premise_id.strip())
    if row is None:
        return None
    return {
        k: row.get(k)
        for k in CUSTOMER_FIELDS
        if k in row and row.get(k) not in (None, "", " ")
    }


def customer_clip_available() -> bool:
    return customer_shp_path().exists()

"""AEP repair labor duration helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "restoration" / "repair_labor_v1.json"


def load_labor_config(path: Path | None = None) -> dict[str, Any]:
    p = Path(os.getenv("REPAIR_LABOR_CONFIG", str(path or DEFAULT_CONFIG)))
    if not p.is_file():
        raise FileNotFoundError(f"Repair labor config missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def repair_duration_hours(
    repair_type: str,
    *,
    workers_per_crew: int,
    quantity: float = 1.0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_labor_config()
    entry = cfg["repairs"].get(repair_type)
    if not entry or not entry.get("configured"):
        raise ValueError(f"Repair type not configured: {repair_type}")
    direct = entry["removal_person_hours"] + entry["installation_person_hours"]
    ilm = float(cfg["indirect_labor_multiplier"])
    hours = direct * quantity * ilm / max(workers_per_crew, 1)
    return {
        "repair_type": repair_type,
        "construction_unit_id": entry.get("construction_unit_id"),
        "description": entry.get("description"),
        "removal_person_hours": entry["removal_person_hours"],
        "installation_person_hours": entry["installation_person_hours"],
        "quantity": quantity,
        "indirect_labor_multiplier": ilm,
        "workers_per_crew": workers_per_crew,
        "central_repair_hours": round(hours, 4),
        "eta_hours_low": round(hours * 0.9, 4),
        "eta_hours_high": round(hours * 1.1, 4),
        "approximate_mapping": entry.get("approximate_mapping", False),
        "mapping_note": entry.get("mapping_note"),
    }

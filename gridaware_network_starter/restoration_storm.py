"""Simulated storm operational overlays (scope quantity + access start delays)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from repair_labor import load_labor_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORM_CONFIG = REPO_ROOT / "config" / "restoration" / "storm_operational_assumptions.json"

DamageSeverity = Literal["minor", "moderate", "major"]
AccessConditions = Literal["normal", "difficult", "restricted"]


def load_storm_config(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_STORM_CONFIG
    return json.loads(p.read_text(encoding="utf-8"))


def resolve_storm_context(
    net: dict[str, Any],
    damaged: set[str],
    *,
    damage_severity: DamageSeverity = "minor",
    access_conditions: AccessConditions = "normal",
    extra_mobilization_hours: float = 0.0,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build per-component quantity and earliest repair start times."""
    cfg = config or load_storm_config()
    sev = cfg["damage_severity"][damage_severity]
    acc = cfg["access_conditions"][access_conditions]
    qty_by_type = sev["quantity_by_repair_type"]
    access_by_type = acc["site_access_hours_by_repair_type"]
    mobilization = float(acc["crew_mobilization_hours"]) + max(0.0, extra_mobilization_hours)

    comp_map = {c["id"]: c for c in net["components"]}
    repair_quantity: dict[str, float] = {}
    access_ready_hours: dict[str, float] = {}

    for cid in damaged:
        comp = comp_map[cid]
        rt = comp["repair_type"]
        repair_quantity[cid] = float(qty_by_type.get(rt, 1.0))
        access_ready_hours[cid] = mobilization + float(access_by_type.get(rt, 0.0))

    explanations: list[str] = []
    if damage_severity != "minor":
        explanations.append(
            f"{sev['label']} storm scope uses increased work quantities on damaged components "
            f"(simulated, not a multiplier on AEP person-hours)."
        )
    if access_conditions != "normal" or extra_mobilization_hours > 0:
        explanations.append(
            "Restoration may be delayed because crews cannot safely begin work at all sites "
            "until mobilization and site access windows are met (simulated operational delay)."
        )

    return {
        "damage_severity": damage_severity,
        "access_conditions": access_conditions,
        "extra_mobilization_hours": extra_mobilization_hours,
        "crew_mobilization_hours": mobilization,
        "repair_quantity_by_component": repair_quantity,
        "access_ready_hours_by_component": access_ready_hours,
        "severity_description": sev["description"],
        "access_description": acc["description"],
        "disclaimer": cfg["disclaimer"],
        "eta_explanations": explanations,
    }


def labor_preview_for_damaged(
    net: dict[str, Any],
    damaged: set[str],
    storm_ctx: dict[str, Any],
    *,
    workers_per_crew: int,
    labor_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Central repair hours per damaged component under storm scope."""
    from repair_labor import repair_duration_hours

    labor = labor_config or load_labor_config()
    comp_map = {c["id"]: c for c in net["components"]}
    rows: list[dict[str, Any]] = []
    for cid in sorted(damaged):
        comp = comp_map[cid]
        qty = storm_ctx["repair_quantity_by_component"].get(cid, 1.0)
        d = repair_duration_hours(
            comp["repair_type"],
            workers_per_crew=workers_per_crew,
            quantity=qty,
            config=labor,
        )
        rows.append(
            {
                "component_id": cid,
                "repair_type": comp["repair_type"],
                "quantity": qty,
                "central_repair_hours": d["central_repair_hours"],
                "access_ready_hours": storm_ctx["access_ready_hours_by_component"].get(cid, 0.0),
            }
        )
    return rows

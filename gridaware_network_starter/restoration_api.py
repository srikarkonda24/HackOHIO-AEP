"""Restoration simulation API (Stage 5A)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from repair_labor import load_labor_config
from restoration_graph import load_network, new_state, snapshot_from_state
from restoration_optimizer import run_restoration_scenario
from restoration_storm import load_storm_config

router = APIRouter(prefix="/restoration", tags=["restoration"])


@router.get("/network")
def get_restoration_network():
    net = load_network()
    labor = load_labor_config()
    src = str(labor.get("source_workbook", ""))
    synthetic = (
        "fixture" in src.lower()
        or "synthetic" in str(labor.get("data_provenance", "")).lower()
        or "minimal" in src.lower()
    )
    return {
        "network": net,
        "labor_references": {
            "config_version": labor["config_version"],
            "duration_formula": labor["duration_formula"],
            "repairs": labor["repairs"],
            "source_workbook": labor.get("source_workbook"),
            "synthetic_labor_warning": synthetic,
        },
    }


@router.get("/labor-config")
def get_labor_config():
    return load_labor_config()


@router.get("/storm-assumptions")
def get_storm_assumptions():
    return load_storm_config()


class OutagePreviewRequest(BaseModel):
    damaged_component_ids: list[str] = Field(default_factory=list, max_length=7)


@router.post("/outage-preview")
def post_outage_preview(body: OutagePreviewRequest):
    net = load_network()
    valid = {c["id"] for c in net["components"]}
    damaged = {c for c in body.damaged_component_ids if c in valid}
    if len(damaged) != len(body.damaged_component_ids):
        raise HTTPException(status_code=400, detail="Unknown equipment selection.")
    snap = snapshot_from_state(net, new_state(net, damaged))
    return {"damaged_component_ids": sorted(damaged), "snapshot": snap}


class RestorationSimRequest(BaseModel):
    damaged_component_ids: list[str] = Field(default_factory=list, max_length=7)
    total_workers: Annotated[int, Field(ge=1, le=64)]
    workers_per_crew: Annotated[int, Field(ge=2, le=8)]
    baseline_repair_order: list[str] | None = None
    enable_step_restoration: bool = True
    damage_severity: Literal["minor", "moderate", "major"] = "minor"
    access_conditions: Literal["normal", "difficult", "restricted"] = "normal"
    extra_mobilization_hours: Annotated[float, Field(ge=0, le=168)] = 0.0


@router.post("/simulate")
def post_restoration_simulate(body: RestorationSimRequest):
    try:
        return run_restoration_scenario(
            damaged_component_ids=body.damaged_component_ids,
            total_workers=body.total_workers,
            workers_per_crew=body.workers_per_crew,
            baseline_order=body.baseline_repair_order,
            enable_step_restoration=body.enable_step_restoration,
            damage_severity=body.damage_severity,
            access_conditions=body.access_conditions,
            extra_mobilization_hours=body.extra_mobilization_hours,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "Infeasible" in msg or "Unknown component" in msg:
            raise HTTPException(
                status_code=400,
                detail="This damage combination cannot be scheduled. Try removing damage or repair upstream equipment first.",
            ) from exc
        raise HTTPException(status_code=400, detail=msg) from exc

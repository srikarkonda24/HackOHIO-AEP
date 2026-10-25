"""Proactive outage alerts API (Stage 6 demo)."""
from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from alert_engine import (
    evaluate_restoration_committed,
    evaluate_restoration_playback,
    evaluate_storm_preparation,
    make_sim_run_id,
)
from alert_session_store import (
    get_or_create_session,
    reset_session,
    session_to_dict,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

_db_path: str | None = None


def configure(db_path: str) -> APIRouter:
    global _db_path
    _db_path = db_path
    return router


def _connect() -> sqlite3.Connection:
    if not _db_path:
        raise HTTPException(status_code=503, detail="Alerts API not configured")
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    return con


class PreferencesBody(BaseModel):
    notifications_enabled: bool = True
    channel: Literal["sms", "email", "in_app"] = "in_app"
    medium_risk_preparation: bool = False


class StormScenarioInputs(BaseModel):
    max_wind_gust_mph: Annotated[float, Field(ge=0, le=150)]
    total_precipitation_in: Annotated[float, Field(ge=0, le=30)]
    min_temperature_f: Annotated[float, Field(ge=-60, le=120)]
    snowfall_in: Annotated[float, Field(ge=0, le=50)]


class RiskPreparationBody(BaseModel):
    premise_id: Annotated[str, Field(min_length=1, max_length=64)]
    storm_scenario: StormScenarioInputs


class RestorationCommittedBody(BaseModel):
    sim_run_id: Annotated[str, Field(min_length=8, max_length=64)]
    initial_snapshot: dict
    group_restoration_times: dict[str, float | None]
    modeled_group_id: str = "RES1"


class RestorationPlaybackBody(BaseModel):
    sim_run_id: Annotated[str, Field(min_length=8, max_length=64)]
    playback_time_hours: Annotated[float, Field(ge=0)]
    modeled_group_id: str = "RES1"
    timeline: list[dict] = Field(default_factory=list)


class SimRunIdBody(BaseModel):
    damaged_component_ids: list[str] = Field(default_factory=list)
    total_workers: int
    workers_per_crew: int
    enable_step_restoration: bool = True
    damage_severity: str = "minor"
    access_conditions: str = "normal"
    extra_mobilization_hours: float = 0
    compare_mode: str = "step"


@router.get("/session/{session_id}")
def get_session(session_id: str):
    sess = get_or_create_session(session_id)
    return session_to_dict(sess)


@router.put("/session/{session_id}/preferences")
def put_preferences(session_id: str, body: PreferencesBody):
    sess = get_or_create_session(session_id)
    sess.preferences.notifications_enabled = body.notifications_enabled
    sess.preferences.channel = body.channel
    sess.preferences.medium_risk_preparation = body.medium_risk_preparation
    return session_to_dict(sess)


@router.post("/session/{session_id}/reset")
def post_reset(session_id: str):
    sess = reset_session(session_id)
    return session_to_dict(sess)


@router.post("/session/{session_id}/mark-read")
def post_mark_read(session_id: str):
    sess = get_or_create_session(session_id)
    for ev in sess.events:
        ev["read"] = True
    return session_to_dict(sess)


@router.post("/session/{session_id}/evaluate/risk-preparation")
def post_evaluate_risk_preparation(session_id: str, body: RiskPreparationBody):
    sess = get_or_create_session(session_id)
    with _connect() as con:
        try:
            result = evaluate_storm_preparation(
                sess,
                con,
                premise_id=body.premise_id,
                max_wind_gust_mph=body.storm_scenario.max_wind_gust_mph,
                total_precipitation_in=body.storm_scenario.total_precipitation_in,
                min_temperature_f=body.storm_scenario.min_temperature_f,
                snowfall_in=body.storm_scenario.snowfall_in,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Premise not found") from exc
    return {**result, "session": session_to_dict(sess)}


@router.post("/session/{session_id}/evaluate/restoration-committed")
def post_evaluate_restoration_committed(session_id: str, body: RestorationCommittedBody):
    sess = get_or_create_session(session_id)
    result = evaluate_restoration_committed(
        sess,
        sim_run_id=body.sim_run_id,
        initial_snapshot=body.initial_snapshot,
        group_restoration_times=body.group_restoration_times,
        modeled_group_id=body.modeled_group_id,
    )
    return {**result, "session": session_to_dict(sess)}


@router.post("/session/{session_id}/evaluate/restoration-playback")
def post_evaluate_restoration_playback(session_id: str, body: RestorationPlaybackBody):
    sess = get_or_create_session(session_id)
    if sess.restoration.last_sim_run_id != body.sim_run_id:
        raise HTTPException(status_code=400, detail="Unknown or stale simulation run.")
    result = evaluate_restoration_playback(
        sess,
        sim_run_id=body.sim_run_id,
        playback_time_hours=body.playback_time_hours,
        modeled_group_id=body.modeled_group_id,
        timeline=body.timeline,
    )
    return {**result, "session": session_to_dict(sess)}


@router.post("/utils/sim-run-id")
def post_sim_run_id(body: SimRunIdBody):
    return {"sim_run_id": make_sim_run_id(body.model_dump())}

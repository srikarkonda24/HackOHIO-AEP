"""Customer historical weather risk assessment API."""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from historical_weather_risk import assess_risk
from network_context_service import build_network_context

router = APIRouter(tags=["customers"])

_db_path: str | None = None


def configure(db_path: str) -> APIRouter:
    global _db_path
    _db_path = db_path
    return router


def _connect() -> sqlite3.Connection:
    if not _db_path:
        raise HTTPException(status_code=503, detail="Risk assessment API not configured")
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    return con


class RiskWeatherInputs(BaseModel):
    max_wind_gust_mph: Annotated[float, Field(ge=0, le=150)]
    total_precipitation_in: Annotated[float, Field(ge=0, le=30)]
    min_temperature_f: Annotated[float, Field(ge=-60, le=120)]
    snowfall_in: Annotated[float, Field(ge=0, le=50)]


@router.post("/customers/{premise_id}/risk-assessment")
def post_customer_risk_assessment(premise_id: str, body: RiskWeatherInputs):
    """
    Relative LOW/MEDIUM/HIGH outage concern from documented historical weather
    enrichment and hazard rules — not a calibrated outage probability.
    """
    with _connect() as con:
        try:
            ctx = build_network_context(con, premise_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Premise not found") from exc

    try:
        return assess_risk(
            premise_id,
            ctx,
            max_wind_gust_mph=body.max_wind_gust_mph,
            total_precipitation_in=body.total_precipitation_in,
            min_temperature_f=body.min_temperature_f,
            snowfall_in=body.snowfall_in,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Risk model parameters not installed; run scripts/build_risk_model_params.py",
        ) from exc

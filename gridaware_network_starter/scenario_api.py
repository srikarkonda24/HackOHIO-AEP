"""Exposure scenario API (M3A)."""
from __future__ import annotations

import sqlite3
from fastapi import APIRouter, HTTPException, Query

from scenario_service import compute_device_unavailable

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _connect(db_path: str):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def configure(db_path: str):
    @router.get("/device-unavailable/summary")
    def scenario_summary(device_key: str = Query(..., min_length=3)):
        """Full dependency counts and premise IDs without coordinate payload."""
        with _connect(db_path) as con:
            try:
                scenario = compute_device_unavailable(
                    con, device_key, include_geometry=False
                )
            except KeyError:
                raise HTTPException(status_code=404, detail="Device not found") from None
        data = scenario.as_dict()
        data.pop("customers", None)
        return data

    @router.get("/device-unavailable")
    def scenario_full(device_key: str = Query(..., min_length=3)):
        """Complete modeled exposure set including all premise coordinates."""
        with _connect(db_path) as con:
            try:
                scenario = compute_device_unavailable(
                    con, device_key, include_geometry=True
                )
            except KeyError:
                raise HTTPException(status_code=404, detail="Device not found") from None
        return scenario.as_dict()

    return router

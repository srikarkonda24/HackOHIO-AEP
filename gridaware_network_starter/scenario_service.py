"""Dependency-based exposure scenarios (simulation only — not confirmed outages)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceUnavailableScenario:
    scenario_type: str
    device_key: str
    device: dict[str, Any]
    modeled_potential_exposure_count: int
    premise_ids: list[str]
    customers: list[dict[str, Any]]
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_type": self.scenario_type,
            "device_key": self.device_key,
            "device": self.device,
            "modeled_potential_exposure_count": self.modeled_potential_exposure_count,
            "premise_count": len(self.premise_ids),
            "returned_customer_points": len(self.customers),
            "premise_ids": self.premise_ids,
            "customers": self.customers,
            "note": self.note,
            "disclaimer": (
                "Simulated device-unavailable scenario based on upstream dependency "
                "membership only. Not a confirmed outage, switching study, or "
                "restoration estimate."
            ),
        }


def compute_device_unavailable(
    con: sqlite3.Connection, device_key: str, *, include_geometry: bool = True
) -> DeviceUnavailableScenario:
    device = con.execute(
        "SELECT * FROM devices WHERE device_key=?", (device_key,)
    ).fetchone()
    if not device:
        raise KeyError(device_key)

    device_dict = dict(device)
    count = con.execute(
        "SELECT COUNT(*) FROM dependencies WHERE device_key=?", (device_key,)
    ).fetchone()[0]

    premise_rows = con.execute(
        "SELECT premise_id FROM dependencies WHERE device_key=? ORDER BY premise_id",
        (device_key,),
    ).fetchall()
    premise_ids = [str(r[0]) for r in premise_rows]

    customers: list[dict[str, Any]] = []
    if include_geometry and premise_ids:
        # Full dependency set — no map-performance cap.
        customers = [
            dict(r)
            for r in con.execute(
                """SELECT p.premise_id, p.longitude, p.latitude, p.circuit_id
                   FROM dependencies dp
                   JOIN premises p ON p.premise_id = dp.premise_id
                   WHERE dp.device_key=?
                   ORDER BY p.premise_id""",
                (device_key,),
            ).fetchall()
        ]

    return DeviceUnavailableScenario(
        scenario_type="device_unavailable",
        device_key=device_key,
        device=device_dict,
        modeled_potential_exposure_count=count,
        premise_ids=premise_ids,
        customers=customers,
        note=(
            "If this device were unavailable in a what-if exercise, these premises "
            "are potentially exposed via indexed upstream dependencies. Actual "
            "isolation and switching are not modeled."
        ),
    )

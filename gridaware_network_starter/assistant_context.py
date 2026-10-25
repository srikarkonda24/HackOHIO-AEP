"""Sanitized, backend-verified context for the outage assistant."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from historical_weather_risk import assess_risk
from network_context_service import build_network_context


def _title_case_city(city: str) -> str:
    return " ".join(
        w[:1].upper() + w[1:].lower() if w else w for w in city.strip().split()
    )


def _customer_explanation(relative_risk: str, active: dict[str, bool]) -> list[str]:
    factors: list[str] = []
    if active.get("severe_wind"):
        factors.append("very strong wind gusts")
    elif active.get("moderate_wind"):
        factors.append("stronger-than-usual winds")
    if active.get("severe_precip"):
        factors.append("heavy rainfall")
    elif active.get("moderate_precip"):
        factors.append("notable rainfall")
    if active.get("freezing"):
        factors.append("freezing temperatures")
    if active.get("any_snowfall"):
        factors.append("snowfall")

    def join_f(parts: list[str]) -> str:
        if len(parts) <= 1:
            return parts[0] if parts else ""
        if len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        return f"{', '.join(parts[:-1])}, and {parts[-1]}"

    if relative_risk == "LOW":
        lines = [
            "These storm conditions are relatively mild compared with historical "
            "conditions in your area."
        ]
        if factors:
            lines.append(
                f"Your scenario includes {join_f(factors)}, but overall it still "
                "aligns with lower-concern weather patterns for this region."
            )
        return lines
    if relative_risk == "MEDIUM":
        if factors:
            cap = [f[:1].upper() + f[1:] for f in factors]
            return [
                f"{join_f(cap)} may increase the likelihood of damage to electrical "
                "equipment during storms like this."
            ]
        return [
            "The weather scenario you selected may increase the likelihood of damage "
            "to electrical equipment compared with typical conditions."
        ]
    if factors:
        return [
            f"With {join_f(factors)}, these conditions resemble weather associated "
            "with significant historical equipment damage in this region."
        ]
    return [
        "Severe storm conditions resemble weather associated with significant "
        "historical equipment damage in this region."
    ]


def build_verified_assistant_context(
    con: sqlite3.Connection,
    premise_id: str,
    *,
    max_wind_gust_mph: float,
    total_precipitation_in: float,
    min_temperature_f: float,
    snowfall_in: float,
) -> dict[str, Any]:
    """Recompute Stage 4 risk on the server; strip sensitive network detail."""
    try:
        network_ctx = build_network_context(con, premise_id)
    except KeyError as exc:
        raise LookupError("Premise not found") from exc

    assessment = assess_risk(
        premise_id,
        network_ctx,
        max_wind_gust_mph=max_wind_gust_mph,
        total_precipitation_in=total_precipitation_in,
        min_temperature_f=min_temperature_f,
        snowfall_in=snowfall_in,
    )

    clip = network_ctx.get("customer_clip") or {}
    city = clip.get("city")
    state = clip.get("state")
    service_area = None
    if city and state:
        service_area = f"{_title_case_city(str(city))}, {str(state).strip().upper()}"

    weather_blob = json.dumps(
        {
            "max_wind_gust_mph": max_wind_gust_mph,
            "total_precipitation_in": total_precipitation_in,
            "min_temperature_f": min_temperature_f,
            "snowfall_in": snowfall_in,
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(
        f"{premise_id}:{assessment['model_version']}:{weather_blob}".encode()
    ).hexdigest()[:16]

    active = assessment["active_weather_condition_flags"]
    return {
        "premise_id": premise_id,
        "service_area": service_area,
        "study_region": assessment["location"].get("study_region"),
        "storm_scenario": {
            "storm_window": "hypothetical_three_day_summary",
            "max_wind_gust_mph": max_wind_gust_mph,
            "total_precipitation_in": total_precipitation_in,
            "min_temperature_f": min_temperature_f,
            "snowfall_in": snowfall_in,
        },
        "relative_risk": assessment["relative_risk"],
        "customer_explanation": _customer_explanation(
            assessment["relative_risk"], active
        ),
        "limitations": list(assessment.get("limitations", []))[:8],
        "assessment_type": assessment["assessment_type"],
        "model_version": assessment["model_version"],
        "assessment_id": digest,
        "disclaimer": (
            "Scenario-based GridAware model output only. Not a live outage, "
            "confirmed restoration time, or outage probability."
        ),
        "evidence_quality_customer": assessment.get("evidence_quality_customer"),
    }


def apply_user_declared_context(
    ctx: dict[str, Any],
    *,
    essential_medical_equipment: bool,
) -> dict[str, Any]:
    ctx = dict(ctx)
    ctx["user_declared_context"] = {
        "relies_on_electricity_for_essential_medical_or_accessibility_equipment": (
            essential_medical_equipment
        ),
        "declaration_source": "customer_checkbox_current_session_only",
        "not_inferred_from_utility_records": True,
    }
    return ctx

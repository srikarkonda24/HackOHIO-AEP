"""Historical weather–informed relative outage risk (Stage 4)."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "config" / "risk_model" / "historical_weather_risk_model.json"
WEATHER_SOURCES = REPO_ROOT / "gridaware_weather_package" / "weather_sources.json"

RelativeRisk = Literal["LOW", "MEDIUM", "HIGH"]
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

_model_cache: dict[str, Any] | None = None
_weather_points_cache: list[dict[str, Any]] | None = None


def load_model() -> dict[str, Any]:
    global _model_cache
    if _model_cache is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Risk model parameters missing: {MODEL_PATH}")
        _model_cache = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    return _model_cache


def load_weather_points() -> list[dict[str, Any]]:
    global _weather_points_cache
    if _weather_points_cache is None:
        raw = json.loads(WEATHER_SOURCES.read_text(encoding="utf-8"))
        _weather_points_cache = [
            {
                "location": item["location"],
                "lat": item["coordinates_returned"][0],
                "lon": item["coordinates_returned"][1],
            }
            for item in raw
        ]
    return _weather_points_cache


def nearest_weather_point(lat: float, lon: float) -> dict[str, Any]:
    points = load_weather_points()
    best = min(
        points,
        key=lambda p: (p["lat"] - lat) ** 2 + (p["lon"] - lon) ** 2,
    )
    dist_deg = math.sqrt((best["lat"] - lat) ** 2 + (best["lon"] - lon) ** 2)
    return {**best, "distance_degrees": round(dist_deg, 4)}


def _max_risk(a: RelativeRisk, b: RelativeRisk) -> RelativeRisk:
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def _percentile_rank(value: float, pct: dict[str, float]) -> str:
    if value >= pct["p90"]:
        return "above_historical_90th_percentile"
    if value >= pct["p75"]:
        return "between_75th_and_90th_percentile"
    if value >= pct["p50"]:
        return "between_median_and_75th_percentile"
    if value >= pct["p25"]:
        return "between_25th_and_median_percentile"
    return "below_25th_percentile"


def _active_conditions(
    w: float, p: float, t: float, s: float, model: dict[str, Any]
) -> dict[str, bool]:
    th = model["enrichment_analysis_thresholds"]
    pooled = model["pooled_three_day_percentiles"]
    return {
        "severe_wind": w >= th["max_wind_gust_mph_gte"],
        "moderate_wind": w >= pooled["max_wind_gust_mph"]["p75"],
        "severe_precip": p >= th["total_precipitation_in_gte"],
        "moderate_precip": p >= pooled["total_precipitation_in"]["p50"],
        "freezing": t <= th["min_temperature_f_lte"],
        "any_snowfall": s > th["snowfall_in_gt"],
    }


def classify_relative_risk(
    *,
    max_wind_gust_mph: float,
    total_precipitation_in: float,
    min_temperature_f: float,
    snowfall_in: float,
) -> tuple[RelativeRisk, int, dict[str, bool]]:
    model = load_model()
    pooled = model["pooled_three_day_percentiles"]
    th = model["enrichment_analysis_thresholds"]
    active = _active_conditions(
        max_wind_gust_mph, total_precipitation_in, min_temperature_f, snowfall_in, model
    )

    calm = (
        max_wind_gust_mph < pooled["max_wind_gust_mph"]["p25"]
        and total_precipitation_in < pooled["total_precipitation_in"]["p25"]
        and snowfall_in == 0
        and min_temperature_f > th["min_temperature_f_lte"]
    )
    if calm:
        score = 0
        base: RelativeRisk = "LOW"
    else:
        score = 0
        if active["severe_wind"]:
            score += 3
        elif active["moderate_wind"]:
            score += 1
        if active["severe_precip"]:
            score += 2
        elif active["moderate_precip"]:
            score += 1
        if active["freezing"]:
            score += 1
        if active["any_snowfall"]:
            if active["freezing"] or active["moderate_wind"]:
                score += 2
            else:
                score += 1
        if score <= 1:
            base = "LOW"
        elif score <= 4:
            base = "MEDIUM"
        else:
            base = "HIGH"

    risk = base
    if max_wind_gust_mph >= pooled["max_wind_gust_mph"]["p95"]:
        risk = _max_risk(risk, "HIGH")
    elif max_wind_gust_mph >= th["max_wind_gust_mph_gte"]:
        risk = _max_risk(risk, "MEDIUM")

    return risk, score, active


def _enrichment_rows_for_conditions(active: dict[str, bool]) -> list[dict[str, Any]]:
    model = load_model()
    rows = model.get("enrichment_table", [])
    out: list[dict[str, Any]] = []
    feature_map = {
        "severe_wind": "Wind gust (3-day max)",
        "severe_precip": "Precipitation (3-day sum)",
        "any_snowfall": "Any snowfall (3-day sum)",
        "freezing": "Freezing (3-day min)",
    }
    for key, feature_prefix in feature_map.items():
        if not active.get(key):
            continue
        for row in rows:
            if not row["feature"].startswith(feature_prefix):
                continue
            if row["damage_group"] == "all types":
                continue
            try:
                n_match = int(row["matching_damage_grid_dates"])
            except (TypeError, ValueError):
                n_match = 0
            out.append(
                {
                    "weather_condition": row["feature"],
                    "damage_category": row["damage_group"],
                    "enrichment_ratio": float(row["enrichment"]),
                    "matching_damage_date_location_pairs": n_match,
                    "total_damage_date_location_pairs_for_type": int(
                        row["damage_grid_dates"]
                    ),
                    "prototype_service_impact_assumption": model[
                        "damage_category_impact_assumptions"
                    ].get(row["damage_group"]),
                    "interpretation": row.get("interpretation", ""),
                    "sparse_evidence": n_match < 10,
                }
            )
    return out


def summarize_infrastructure_context(network_context: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    clip = network_context.get("customer_clip") or {}
    city = clip.get("city")
    state = clip.get("state")
    if city and state:
        lines.append(f"Service location indexed near {city}, {state}.")
    kind = clip.get("kind_of_se")
    if kind:
        lines.append(
            f"Customer records list service type as {str(kind).lower()}; "
            "this does not mean the entire upstream supply path is underground."
        )
    if network_context.get("service_transformer"):
        lines.append(
            "A recorded service transformer location is linked in utility data."
        )
    n = network_context.get("upstream_device_count", 0)
    if n:
        lines.append(
            f"The premise appears in an upstream equipment index with {n} associated "
            "devices; order in that list is not a verified physical path."
        )
    lines.append(
        "Historical damage patterns in the region are not proof that this premise "
        "experienced a customer outage during past storms."
    )
    return lines


def build_explanation(
    risk: RelativeRisk,
    active: dict[str, bool],
    score: int,
    weather_point: str,
) -> str:
    drivers: list[str] = []
    if active["severe_wind"]:
        drivers.append("very strong wind gusts for this region’s historical 3-day windows")
    elif active["moderate_wind"]:
        drivers.append("elevated wind for typical southwest Virginia conditions")
    if active["severe_precip"]:
        drivers.append("heavy total precipitation similar to dates linked to many damage reports")
    elif active["moderate_precip"]:
        drivers.append("moderate precipitation")
    if active["freezing"]:
        drivers.append("freezing minimum temperatures")
    if active["any_snowfall"]:
        drivers.append("snowfall during the window")
    if not drivers:
        drivers.append("weather generally mild relative to historical storm windows")

    driver_text = ", ".join(drivers)
    return (
        f"Relative outage concern is {risk} for hypothetical 3-day storm conditions "
        f"compared to ERA5 history near weather sample '{weather_point}'. "
        f"Key factors: {driver_text}. "
        f"This uses a documented hazard score ({score}) from data-derived thresholds "
        f"and percentiles—not a verified outage probability. "
        "Historical AEP damage enrichments are shown separately as context."
    )


def assess_risk(
    premise_id: str,
    network_context: dict[str, Any],
    *,
    max_wind_gust_mph: float,
    total_precipitation_in: float,
    min_temperature_f: float,
    snowfall_in: float,
) -> dict[str, Any]:
    model = load_model()
    premise = network_context["premise"]
    wp = nearest_weather_point(float(premise["latitude"]), float(premise["longitude"]))
    loc_pct = (
        model["per_location_three_day_percentiles"]
        .get(wp["location"], {})
        .get("three_day_window_percentiles", model["pooled_three_day_percentiles"])
    )
    pooled = model["pooled_three_day_percentiles"]

    risk, score, active = classify_relative_risk(
        max_wind_gust_mph=max_wind_gust_mph,
        total_precipitation_in=total_precipitation_in,
        min_temperature_f=min_temperature_f,
        snowfall_in=snowfall_in,
    )
    associations = _enrichment_rows_for_conditions(active)
    sparse_drivers = [a for a in associations if a["sparse_evidence"]]

    comparisons = {
        "storm_window": model["storm_window"]["definition"],
        "weather_sample_location": wp["location"],
        "weather_sample_distance_degrees": wp["distance_degrees"],
        "max_wind_gust_mph": {
            "value": max_wind_gust_mph,
            "historical_percentile_band_pooled": _percentile_rank(
                max_wind_gust_mph, pooled["max_wind_gust_mph"]
            ),
            "enrichment_threshold_mph": model["enrichment_analysis_thresholds"][
                "max_wind_gust_mph_gte"
            ],
        },
        "total_precipitation_in": {
            "value": total_precipitation_in,
            "historical_percentile_band_pooled": _percentile_rank(
                total_precipitation_in, pooled["total_precipitation_in"]
            ),
            "enrichment_threshold_in": model["enrichment_analysis_thresholds"][
                "total_precipitation_in_gte"
            ],
        },
        "min_temperature_f": {
            "value": min_temperature_f,
            "historical_percentile_band_pooled": _percentile_rank(
                min_temperature_f, pooled["min_temperature_f"]
            ),
            "freezing_threshold_f": model["enrichment_analysis_thresholds"][
                "min_temperature_f_lte"
            ],
        },
        "snowfall_in": {
            "value": snowfall_in,
            "historical_percentile_band_at_location": _percentile_rank(
                snowfall_in, loc_pct.get("snowfall_in", pooled["snowfall_in"])
            ),
        },
    }

    from risk_evidence_display import build_evidence_quality_customer_view

    payload = {
        "premise_id": premise_id,
        "location": {
            "study_region": model["study_region"],
            "premise_latitude": premise["latitude"],
            "premise_longitude": premise["longitude"],
            "weather_sample_location": wp["location"],
        },
        "relative_risk": risk,
        "assessment_type": "historical_weather_informed_relative_outage_risk",
        "weather_inputs": {
            "storm_window": "three_day_summary",
            "max_wind_gust_mph": max_wind_gust_mph,
            "total_precipitation_in": total_precipitation_in,
            "min_temperature_f": min_temperature_f,
            "snowfall_in": snowfall_in,
        },
        "historical_weather_comparisons": comparisons,
        "hazard_score": score,
        "active_weather_condition_flags": active,
        "applicable_damage_associations": associations,
        "damage_impact_assumptions_context": {
            k: v
            for k, v in model["damage_category_impact_assumptions"].items()
            if not k.startswith("_")
        },
        "infrastructure_context_summary": summarize_infrastructure_context(
            network_context
        ),
        "explanation": build_explanation(risk, active, score, wp["location"]),
        "evidence_quality": {
            "distinct_arcos_report_dates": model["data_summary"]["distinct_report_dates"],
            "distinct_damage_date_location_pairs": model["data_summary"][
                "distinct_date_grid_pairs"
            ],
            "sparse_association_rows": len(sparse_drivers),
            "note": (
                "Low pair counts (especially Damaged Light) should not be read as "
                "strong outage evidence; enrichments are descriptive only."
            ),
        },
        "limitations": model["limitations"]
        + [
            "Scenario inputs are hypothetical, not a live forecast.",
            "Underground service at the meter does not imply an all-underground feed.",
        ],
        "model_version": model["model_version"],
    }
    payload["evidence_quality_customer"] = build_evidence_quality_customer_view(payload)
    return payload

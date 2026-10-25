"""Build documented risk-model JSON from ERA5 CSV and enrichment analysis."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEATHER_CSV = ROOT / "gridaware_weather_package" / "historical_weather_era5.csv"
ENRICHMENT_CSV = (
    ROOT
    / "gridaware_revised_model_analysis"
    / "gridaware_model_review"
    / "three_day_weather_damage_enrichment.csv"
)
OUT = ROOT / "config" / "risk_model" / "historical_weather_risk_model.json"
CM_PER_IN = 2.54


def load_daily() -> dict[str, list[dict]]:
    by_loc: dict[str, list[dict]] = defaultdict(list)
    with WEATHER_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_loc[row["location"]].append(
                {
                    "date": row["date"],
                    "wind_gust_mph": float(row["wind_gust_mph"]),
                    "precip_in": float(row["precip_in"]),
                    "min_temp_f": float(row["min_temp_f"]),
                    "snowfall_cm": float(row["snowfall_cm"]),
                }
            )
    for loc in by_loc:
        by_loc[loc].sort(key=lambda r: r["date"])
    return by_loc


def three_day_windows(rows: list[dict]) -> list[dict]:
    out = []
    for i in range(2, len(rows)):
        w = rows[i - 2 : i + 1]
        out.append(
            {
                "max_wind_gust_mph": max(x["wind_gust_mph"] for x in w),
                "total_precipitation_in": sum(x["precip_in"] for x in w),
                "min_temperature_f": min(x["min_temp_f"] for x in w),
                "snowfall_in": sum(x["snowfall_cm"] for x in w) / CM_PER_IN,
            }
        )
    return out


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def pctiles(vals: list[float]) -> dict[str, float]:
    s = sorted(vals)
    return {
        "p25": round(percentile(s, 0.25), 4),
        "p50": round(percentile(s, 0.50), 4),
        "p75": round(percentile(s, 0.75), 4),
        "p90": round(percentile(s, 0.90), 4),
        "p95": round(percentile(s, 0.95), 4),
        "count": len(s),
    }


def main() -> None:
    by_loc = load_daily()
    pooled: list[dict] = []
    per_location: dict[str, dict] = {}
    for loc, rows in by_loc.items():
        windows = three_day_windows(rows)
        pooled.extend(windows)
        per_location[loc] = {
            "three_day_window_percentiles": {
                "max_wind_gust_mph": pctiles([w["max_wind_gust_mph"] for w in windows]),
                "total_precipitation_in": pctiles(
                    [w["total_precipitation_in"] for w in windows]
                ),
                "min_temperature_f": pctiles([w["min_temperature_f"] for w in windows]),
                "snowfall_in": pctiles([w["snowfall_in"] for w in windows]),
            }
        }

    pooled_pct = {
        "max_wind_gust_mph": pctiles([w["max_wind_gust_mph"] for w in pooled]),
        "total_precipitation_in": pctiles([w["total_precipitation_in"] for w in pooled]),
        "min_temperature_f": pctiles([w["min_temperature_f"] for w in pooled]),
        "snowfall_in": pctiles([w["snowfall_in"] for w in pooled]),
    }

    enrichment_rows = []
    with ENRICHMENT_CSV.open(newline="", encoding="utf-8") as f:
        enrichment_rows = list(csv.DictReader(f))

    damage_impact_assumptions = {
        "Damaged Wire": "HIGH",
        "Damaged Pole": "MEDIUM",
        "Damaged Switch": "MEDIUM",
        "Damaged Equipment": "MEDIUM",
        "Damaged Light": "LOW",
        "_note": "Qualitative service-interruption modeling assumptions only; not measured outage rates.",
    }

    payload = {
        "model_version": "historical_weather_informed_v1",
        "storm_window": {
            "definition": "three_day_summary",
            "description": (
                "Scenario inputs are interpreted as a 3-day storm window summary: "
                "maximum gust, summed liquid precipitation, minimum temperature, and "
                "summed snowfall — matching the historical ARCOS enrichment analysis."
            ),
        },
        "study_region": "AEP southwest Virginia (four ERA5 sample grid points)",
        "weather_points": list(by_loc.keys()),
        "default_weather_point_for_unknown_coords": "vinton_customer",
        "data_summary": json.loads(
            (
                ROOT
                / "gridaware_revised_model_analysis"
                / "gridaware_model_review"
                / "data_summary.json"
            ).read_text(encoding="utf-8")
        ),
        "pooled_three_day_percentiles": pooled_pct,
        "per_location_three_day_percentiles": per_location,
        "enrichment_analysis_thresholds": {
            "max_wind_gust_mph_gte": 40.5,
            "total_precipitation_in_gte": 0.9464999999999996,
            "min_temperature_f_lte": 32.0,
            "snowfall_in_gt": 0.0,
            "source": "three_day_weather_damage_enrichment.csv (top-decile / freezing / any-snow conditions)",
        },
        "classification_rule": {
            "name": "hazard_tier_with_wind_floor",
            "calm_weather_guard": {
                "requires_all": [
                    "max_wind_gust_mph < pooled_p25_wind",
                    "total_precipitation_in < pooled_p25_precip",
                    "snowfall_in == 0",
                    "min_temperature_f > 32",
                ],
                "relative_risk": "LOW",
            },
            "hazard_points": {
                "severe_wind_gte_enrichment_threshold": 3,
                "moderate_wind_gte_p75": 1,
                "severe_precip_gte_enrichment_threshold": 2,
                "moderate_precip_gte_p50": 1,
                "freezing_min_temp_lte_32f": 1,
                "snowfall_in_gt_0_with_freezing_or_moderate_wind": 2,
                "snowfall_in_gt_0_alone": 1,
            },
            "bands_from_hazard_score": {"LOW": "score <= 1", "MEDIUM": "2 <= score <= 4", "HIGH": "score >= 5"},
            "wind_monotonicity_floor": {
                "gte_enrichment_wind_threshold": "MEDIUM",
                "gte_p95_wind": "HIGH",
            },
            "sparse_evidence": {
                "min_enrichment_matching_pairs_for_driver_narrative": 10,
                "categories_with_low_support": ["Damaged Light"],
            },
        },
        "damage_category_impact_assumptions": damage_impact_assumptions,
        "enrichment_table": enrichment_rows,
        "limitations": [
            "Enrichment E(C,d) is descriptive association, not outage probability.",
            "Only 55 distinct ARCOS report dates; February 2025 cluster dominates.",
            "ERA5 at four coarse points; not on-site measurements.",
            "Damage categories are not confirmed customer outage labels.",
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print("Pooled p90 wind:", pooled_pct["max_wind_gust_mph"]["p90"])


if __name__ == "__main__":
    main()

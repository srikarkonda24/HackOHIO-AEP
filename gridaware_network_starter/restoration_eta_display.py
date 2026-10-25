"""Customer-facing restoration ETA day buckets (hours remain internal elsewhere)."""
from __future__ import annotations

RESTORATION_ETA_CATEGORY_LABELS: tuple[str, ...] = (
    "Within 1 day",
    "1–2 days",
    "2–3 days",
    "3–4 days",
    "4–5 days",
    "5–7 days (within 1 week)",
    "More than 1 week",
)

_BUCKET_UPPER_INCLUSIVE_HOURS = (24, 48, 72, 96, 120, 168, float("inf"))

NO_OUTAGE_LABEL = "No simulated outage"


def restoration_hours_to_category(hours: float) -> str:
    if hours <= _BUCKET_UPPER_INCLUSIVE_HOURS[0]:
        return RESTORATION_ETA_CATEGORY_LABELS[0]
    for i in range(1, len(_BUCKET_UPPER_INCLUSIVE_HOURS)):
        if hours <= _BUCKET_UPPER_INCLUSIVE_HOURS[i]:
            return RESTORATION_ETA_CATEGORY_LABELS[i]
    return RESTORATION_ETA_CATEGORY_LABELS[-1]


def _category_index(hours: float) -> int:
    return RESTORATION_ETA_CATEGORY_LABELS.index(restoration_hours_to_category(hours))


def restoration_uncertainty_band_hours(central_hours: float) -> tuple[float, float]:
    return central_hours * 0.9, central_hours * 1.1


def restoration_eta_category_range(low_hours: float, high_hours: float) -> list[str]:
    lo, hi = min(low_hours, high_hours), max(low_hours, high_hours)
    start, end = _category_index(lo), _category_index(hi)
    return list(RESTORATION_ETA_CATEGORY_LABELS[start : end + 1])


def format_restoration_eta_category_range(labels: list[str]) -> str:
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]} to {labels[-1]}"


def format_customer_restoration_eta(
    *,
    is_initially_powered: bool,
    restoration_hours: float | None,
) -> str:
    if is_initially_powered:
        return NO_OUTAGE_LABEL
    if restoration_hours is None:
        return "Restoration time unavailable for this scenario"
    low, high = restoration_uncertainty_band_hours(restoration_hours)
    labels = restoration_eta_category_range(low, high)
    return format_restoration_eta_category_range(labels)

"""Customer ETA day categories for alert rules (mirrors frontend restoration ETA)."""
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

NO_OUTAGE_LABEL = "No simulated outage"
_BUCKET_UPPER_INCLUSIVE_HOURS = (24, 48, 72, 96, 120, 168, float("inf"))


def restoration_hours_to_category(hours: float) -> str:
    if hours <= _BUCKET_UPPER_INCLUSIVE_HOURS[0]:
        return RESTORATION_ETA_CATEGORY_LABELS[0]
    for i in range(1, len(_BUCKET_UPPER_INCLUSIVE_HOURS)):
        if hours <= _BUCKET_UPPER_INCLUSIVE_HOURS[i]:
            return RESTORATION_ETA_CATEGORY_LABELS[i]
    return RESTORATION_ETA_CATEGORY_LABELS[-1]


def eta_category_for_home(
    *,
    initially_powered: bool,
    restoration_hours: float | None,
) -> str | None:
    if initially_powered:
        return None
    if restoration_hours is None:
        return None
    return restoration_hours_to_category(float(restoration_hours))

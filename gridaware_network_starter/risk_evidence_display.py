"""Customer-facing evidence quality labels (not outage probability)."""
from __future__ import annotations

from typing import Any

LIMITED_SUMMARY = (
    "Based on historical weather and equipment-damage records. "
    "Verified customer outage outcomes were not available."
)
INSUFFICIENT_SUMMARY = (
    "Not enough historical model data was available to support a reliable "
    "evidence summary for this scenario."
)


def build_evidence_quality_customer_view(assessment: dict[str, Any]) -> dict[str, str]:
    """
    Conservative classification for AEP-style confidence disclosure.
    Does not alter relative_risk or hazard_score.
    """
    eq = assessment.get("evidence_quality")
    if not isinstance(eq, dict) or not eq:
        return {
            "level": "insufficient",
            "label": "Insufficient evidence",
            "summary": INSUFFICIENT_SUMMARY,
        }

    pairs = eq.get("distinct_damage_date_location_pairs")
    if pairs is not None and int(pairs) <= 0:
        return {
            "level": "insufficient",
            "label": "Insufficient evidence",
            "summary": INSUFFICIENT_SUMMARY,
        }

    sparse_rows = int(eq.get("sparse_association_rows") or 0)
    associations = assessment.get("applicable_damage_associations") or []
    active_sparse = [a for a in associations if a.get("sparse_evidence")]

    summary = LIMITED_SUMMARY
    if sparse_rows > 0 and associations and len(active_sparse) == len(associations):
        summary = (
            "Based on historical weather and equipment-damage records, but active "
            "conditions rely on sparse historical damage samples. Verified customer "
            "outage outcomes were not available."
        )

    return {
        "level": "limited",
        "label": "Limited",
        "summary": summary,
    }

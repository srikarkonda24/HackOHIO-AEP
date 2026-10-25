"""Evidence quality customer display."""
from risk_evidence_display import build_evidence_quality_customer_view


def test_limited_by_default_with_model_data():
    view = build_evidence_quality_customer_view(
        {
            "relative_risk": "HIGH",
            "evidence_quality": {
                "distinct_damage_date_location_pairs": 500,
                "sparse_association_rows": 0,
            },
            "applicable_damage_associations": [],
        }
    )
    assert view["label"] == "Limited"
    assert "outage outcomes" in view["summary"].lower()


def test_insufficient_without_pairs():
    view = build_evidence_quality_customer_view(
        {
            "evidence_quality": {"distinct_damage_date_location_pairs": 0},
        }
    )
    assert view["label"] == "Insufficient evidence"

import { describe, expect, it } from "vitest";
import { evidenceQualityFromAssessment } from "./riskEvidenceQuality";
import type { RiskAssessmentResponse } from "./riskAssessmentTypes";

function minimal(overrides: Partial<RiskAssessmentResponse> = {}): RiskAssessmentResponse {
  return {
    premise_id: "000052580",
    location: {
      study_region: "SW VA",
      premise_latitude: 0,
      premise_longitude: 0,
      weather_sample_location: "x",
    },
    relative_risk: "HIGH",
    assessment_type: "test",
    weather_inputs: {
      storm_window: "three_day_summary",
      max_wind_gust_mph: 50,
      total_precipitation_in: 1,
      min_temperature_f: 30,
      snowfall_in: 0,
    },
    historical_weather_comparisons: {},
    hazard_score: 5,
    active_weather_condition_flags: {},
    applicable_damage_associations: [],
    damage_impact_assumptions_context: {},
    infrastructure_context_summary: [],
    explanation: "tech",
    evidence_quality: {
      distinct_damage_date_location_pairs: 100,
      sparse_association_rows: 0,
    },
    limitations: [],
    model_version: "v1",
    ...overrides,
  };
}

describe("evidenceQualityFromAssessment", () => {
  it("uses backend evidence_quality_customer when present", () => {
    const d = evidenceQualityFromAssessment(
      minimal({
        evidence_quality_customer: {
          level: "limited",
          label: "Limited",
          summary: "Verified customer outage outcomes were not available.",
        },
      }),
    );
    expect(d?.label).toBe("Limited");
    expect(d?.summary).toMatch(/outage outcomes/i);
  });

  it("does not conflate HIGH risk with strong evidence", () => {
    const d = evidenceQualityFromAssessment(
      minimal({
        relative_risk: "HIGH",
        evidence_quality_customer: {
          level: "limited",
          label: "Limited",
          summary: "Based on historical weather and equipment-damage records.",
        },
      }),
    );
    expect(d?.level).toBe("limited");
  });

  it("returns insufficient when pairs are zero", () => {
    const d = evidenceQualityFromAssessment(
      minimal({
        evidence_quality: { distinct_damage_date_location_pairs: 0 },
      }),
    );
    expect(d?.label).toBe("Insufficient evidence");
  });
});

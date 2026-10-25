import { describe, expect, it } from "vitest";
import {
  buildCustomerRiskExplanation,
  formatCompactLocation,
} from "./customerRiskExplanation";
import type { CustomerNetworkContext } from "./networkContextTypes";
import type { RiskAssessmentResponse } from "./riskAssessmentTypes";

function minimalResult(
  overrides: Partial<RiskAssessmentResponse> = {},
): RiskAssessmentResponse {
  return {
    premise_id: "000052580",
    location: {
      study_region: "SW VA",
      premise_latitude: 37.28,
      premise_longitude: -79.73,
      weather_sample_location: "Sample",
    },
    relative_risk: "LOW",
    assessment_type: "test",
    weather_inputs: {
      storm_window: "three_day_summary",
      max_wind_gust_mph: 15,
      total_precipitation_in: 0,
      min_temperature_f: 50,
      snowfall_in: 0,
    },
    historical_weather_comparisons: {},
    hazard_score: 0,
    active_weather_condition_flags: {
      severe_wind: false,
      moderate_wind: false,
      severe_precip: false,
      moderate_precip: false,
      freezing: false,
      any_snowfall: false,
    },
    applicable_damage_associations: [],
    damage_impact_assumptions_context: {},
    infrastructure_context_summary: [],
    explanation: "Technical backend explanation with ERA5 and hazard score.",
    evidence_quality: {},
    limitations: [],
    model_version: "test",
    ...overrides,
  };
}

describe("formatCompactLocation", () => {
  it("formats city and state for customer display", () => {
    const label = formatCompactLocation({
      premise_id: "1",
      customer_clip: { city: "VINTON", state: "VA" },
    } as unknown as CustomerNetworkContext);
    expect(label).toBe("Vinton, VA");
  });
});

describe("buildCustomerRiskExplanation", () => {
  it("uses plain language without ERA5 or hazard score jargon", () => {
    const text = buildCustomerRiskExplanation(minimalResult()).join(" ");
    expect(text).not.toMatch(/ERA5|hazard score|enrichment/i);
    expect(text).toMatch(/relatively mild/i);
  });

  it("reflects API relative_risk HIGH with active wind factors", () => {
    const lines = buildCustomerRiskExplanation(
      minimalResult({
        relative_risk: "HIGH",
        active_weather_condition_flags: {
          severe_wind: true,
          moderate_wind: true,
          severe_precip: false,
          moderate_precip: false,
          freezing: false,
          any_snowfall: false,
        },
      }),
    );
    expect(lines.join(" ")).toMatch(/very strong wind|historical equipment damage/i);
  });

  it("does not replace relative_risk from frontend logic", () => {
    const low = buildCustomerRiskExplanation(minimalResult({ relative_risk: "LOW" }));
    const high = buildCustomerRiskExplanation(
      minimalResult({ relative_risk: "HIGH", hazard_score: 99 }),
    );
    expect(low.join(" ")).toMatch(/mild/i);
    expect(high.join(" ")).toMatch(/significant historical/i);
  });
});

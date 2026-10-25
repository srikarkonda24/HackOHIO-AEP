import { describe, expect, it } from "vitest";
import { RISK_DEMO_PRESETS } from "./riskAssessmentTypes";

describe("RISK_DEMO_PRESETS", () => {
  it("defines mild, wind, and winter presets with four weather fields", () => {
    for (const key of ["mild", "wind", "winter"] as const) {
      const p = RISK_DEMO_PRESETS[key];
      expect(p.label.length).toBeGreaterThan(0);
      expect(p.inputs.max_wind_gust_mph).toBeGreaterThanOrEqual(0);
      expect(p.inputs.total_precipitation_in).toBeGreaterThanOrEqual(0);
      expect(p.inputs.snowfall_in).toBeGreaterThanOrEqual(0);
    }
  });

  it("orders wind severity across presets", () => {
    expect(RISK_DEMO_PRESETS.wind.inputs.max_wind_gust_mph).toBeGreaterThan(
      RISK_DEMO_PRESETS.mild.inputs.max_wind_gust_mph,
    );
  });
});

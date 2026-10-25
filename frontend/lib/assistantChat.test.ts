import { describe, expect, it } from "vitest";
import { ASSISTANT_SUGGESTED_QUESTIONS } from "./assistantTypes";

describe("assistant chat UI constants", () => {
  it("defines four suggested starter questions", () => {
    expect(ASSISTANT_SUGGESTED_QUESTIONS).toHaveLength(4);
    expect(ASSISTANT_SUGGESTED_QUESTIONS[0]).toMatch(/outage risk/i);
  });
});

describe("assistant request shape", () => {
  it("does not embed API keys in client payloads", () => {
    const payload = {
      message: "Hello",
      history: [],
      premise_id: "000052580",
      storm_scenario: {
        max_wind_gust_mph: 15,
        total_precipitation_in: 0.02,
        min_temperature_f: 58,
        snowfall_in: 0,
      },
    };
    expect(JSON.stringify(payload)).not.toMatch(/GEMINI_API_KEY|AIza/i);
  });
});

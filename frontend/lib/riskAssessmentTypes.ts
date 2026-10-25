export type RelativeRisk = "LOW" | "MEDIUM" | "HIGH";

export interface RiskWeatherInputs {
  max_wind_gust_mph: number;
  total_precipitation_in: number;
  min_temperature_f: number;
  snowfall_in: number;
}

export interface RiskAssessmentResponse {
  premise_id: string;
  location: {
    study_region: string;
    premise_latitude: number;
    premise_longitude: number;
    weather_sample_location: string;
  };
  relative_risk: RelativeRisk;
  assessment_type: string;
  weather_inputs: RiskWeatherInputs & { storm_window: string };
  historical_weather_comparisons: Record<string, unknown>;
  hazard_score: number;
  active_weather_condition_flags: Record<string, boolean>;
  applicable_damage_associations: Array<{
    weather_condition: string;
    damage_category: string;
    enrichment_ratio: number;
    matching_damage_date_location_pairs: number;
    prototype_service_impact_assumption: string | null;
    sparse_evidence: boolean;
  }>;
  damage_impact_assumptions_context: Record<string, string>;
  infrastructure_context_summary: string[];
  explanation: string;
  evidence_quality: Record<string, unknown>;
  evidence_quality_customer?: {
    level: "limited" | "insufficient";
    label: string;
    summary: string;
  };
  limitations: string[];
  model_version: string;
}

export const RISK_DEMO_PRESETS: Record<
  string,
  { label: string; inputs: RiskWeatherInputs }
> = {
  mild: {
    label: "Mild Weather",
    inputs: {
      max_wind_gust_mph: 15,
      total_precipitation_in: 0.02,
      min_temperature_f: 58,
      snowfall_in: 0,
    },
  },
  wind: {
    label: "Severe Windstorm",
    inputs: {
      max_wind_gust_mph: 48,
      total_precipitation_in: 0.15,
      min_temperature_f: 42,
      snowfall_in: 0,
    },
  },
  winter: {
    label: "Winter Storm",
    inputs: {
      max_wind_gust_mph: 35,
      total_precipitation_in: 0.55,
      min_temperature_f: 26,
      snowfall_in: 3,
    },
  },
};

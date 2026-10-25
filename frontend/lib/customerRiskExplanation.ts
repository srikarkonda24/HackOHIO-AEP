import type { CustomerNetworkContext } from "./networkContextTypes";
import type { RiskAssessmentResponse } from "./riskAssessmentTypes";

function titleCaseWord(word: string): string {
  if (!word) return word;
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}

/** Compact location label for the customer UI (e.g. "Vinton, VA"). */
export function formatCompactLocation(ctx: CustomerNetworkContext): string | null {
  const clip = ctx.customer_clip;
  if (!clip) return null;
  const city = clip.city;
  const state = clip.state;
  if (typeof city !== "string" || typeof state !== "string") return null;
  const formattedCity = city
    .trim()
    .split(/\s+/)
    .map(titleCaseWord)
    .join(" ");
  return `${formattedCity}, ${state.trim().toUpperCase()}`;
}

function joinFactors(factors: string[]): string {
  if (factors.length === 1) return factors[0];
  if (factors.length === 2) return `${factors[0]} and ${factors[1]}`;
  return `${factors.slice(0, -1).join(", ")}, and ${factors[factors.length - 1]}`;
}

function activeWeatherFactorPhrases(
  active: RiskAssessmentResponse["active_weather_condition_flags"],
): string[] {
  const factors: string[] = [];
  if (active.severe_wind) factors.push("very strong wind gusts");
  else if (active.moderate_wind) factors.push("stronger-than-usual winds");
  if (active.severe_precip) factors.push("heavy rainfall");
  else if (active.moderate_precip) factors.push("notable rainfall");
  if (active.freezing) factors.push("freezing temperatures");
  if (active.any_snowfall) factors.push("snowfall");
  return factors;
}

/**
 * Plain-language summary for customers. Uses API relative_risk and active
 * weather flags only — does not recompute the model.
 */
export function buildCustomerRiskExplanation(
  result: RiskAssessmentResponse,
): string[] {
  const factors = activeWeatherFactorPhrases(result.active_weather_condition_flags);
  const factorClause = factors.length ? joinFactors(factors) : null;

  switch (result.relative_risk) {
    case "LOW":
      if (!factorClause) {
        return [
          "These storm conditions are relatively mild compared with historical conditions in your area.",
        ];
      }
      return [
        "These storm conditions are relatively mild compared with historical conditions in your area.",
        `Your scenario includes ${factorClause}, but overall it still aligns with lower-concern weather patterns for this region.`,
      ];
    case "MEDIUM":
      if (factorClause) {
        return [
          `${joinFactors(factors.map((f) => f.charAt(0).toUpperCase() + f.slice(1)))} may increase the likelihood of damage to electrical equipment during storms like this.`,
        ];
      }
      return [
        "The weather scenario you selected may increase the likelihood of damage to electrical equipment compared with typical conditions.",
      ];
    case "HIGH":
      if (factorClause) {
        return [
          `With ${factorClause}, these conditions resemble weather associated with significant historical equipment damage in this region.`,
        ];
      }
      return [
        "Severe storm conditions resemble weather associated with significant historical equipment damage in this region.",
      ];
    default:
      return [result.explanation];
  }
}

export const RISK_RESULT_LABEL: Record<
  RiskAssessmentResponse["relative_risk"],
  string
> = {
  LOW: "Low outage risk",
  MEDIUM: "Medium outage risk",
  HIGH: "High outage risk",
};

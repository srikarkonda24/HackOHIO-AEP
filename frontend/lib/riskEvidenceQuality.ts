import type { RiskAssessmentResponse } from "./riskAssessmentTypes";

export interface EvidenceQualityDisplay {
  label: string;
  summary: string;
  level: "limited" | "insufficient";
}

export function evidenceQualityFromAssessment(
  result: RiskAssessmentResponse | null | undefined,
): EvidenceQualityDisplay | null {
  if (!result) return null;
  const fromApi = result.evidence_quality_customer as
    | { level?: string; label?: string; summary?: string }
    | undefined;
  if (fromApi?.label && fromApi?.summary) {
    return {
      label: fromApi.label,
      summary: fromApi.summary,
      level: fromApi.level === "insufficient" ? "insufficient" : "limited",
    };
  }
  const eq = result.evidence_quality;
  if (!eq || typeof eq !== "object") {
    return {
      label: "Insufficient evidence",
      summary:
        "Not enough historical model data was available to support a reliable evidence summary for this scenario.",
      level: "insufficient",
    };
  }
  const pairs = eq.distinct_damage_date_location_pairs;
  if (typeof pairs === "number" && pairs <= 0) {
    return {
      label: "Insufficient evidence",
      summary:
        "Not enough historical model data was available to support a reliable evidence summary for this scenario.",
      level: "insufficient",
    };
  }
  return {
    label: "Limited",
    summary:
      "Based on historical weather and equipment-damage records. Verified customer outage outcomes were not available.",
    level: "limited",
  };
}

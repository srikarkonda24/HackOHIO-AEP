import type { RiskWeatherInputs } from "./riskAssessmentTypes";

export interface AssistantStatusResponse {
  llm_configured: boolean;
  provider: string;
  message: string;
  model?: string | null;
}

export interface AssistantChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantChatRequest {
  message: string;
  history: AssistantChatHistoryMessage[];
  premise_id: string;
  storm_scenario: RiskWeatherInputs;
  essential_medical_equipment?: boolean;
}

export interface AssistantChatResponse {
  reply: string;
  assessment_id: string;
  relative_risk: "LOW" | "MEDIUM" | "HIGH";
  configured: boolean;
}

export const ASSISTANT_SUGGESTED_QUESTIONS = [
  "Why is my outage risk high?",
  "What should I do before the storm?",
  "What could delay restoration?",
  "How does GridAware calculate my risk?",
] as const;

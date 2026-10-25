import { API_BASE } from "./constants";
import type { AlertPreferences, AlertSessionResponse } from "./alertTypes";
import type { RiskWeatherInputs } from "./riskAssessmentTypes";
import { ApiError } from "./api";

async function alertFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export function getAlertSession(sessionId: string): Promise<AlertSessionResponse> {
  return alertFetch(`/alerts/session/${encodeURIComponent(sessionId)}`);
}

export function putAlertPreferences(
  sessionId: string,
  prefs: AlertPreferences,
): Promise<AlertSessionResponse> {
  return alertFetch(`/alerts/session/${encodeURIComponent(sessionId)}/preferences`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(prefs),
  });
}

export function resetAlertSession(sessionId: string): Promise<AlertSessionResponse> {
  return alertFetch(`/alerts/session/${encodeURIComponent(sessionId)}/reset`, {
    method: "POST",
  });
}

export function markAlertsRead(sessionId: string): Promise<AlertSessionResponse> {
  return alertFetch(`/alerts/session/${encodeURIComponent(sessionId)}/mark-read`, {
    method: "POST",
  });
}

export function evaluateRiskPreparation(
  sessionId: string,
  premiseId: string,
  stormScenario: RiskWeatherInputs,
): Promise<{ created: boolean; session: AlertSessionResponse }> {
  return alertFetch(
    `/alerts/session/${encodeURIComponent(sessionId)}/evaluate/risk-preparation`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ premise_id: premiseId, storm_scenario: stormScenario }),
    },
  );
}

export function computeSimRunId(payload: Record<string, unknown>): Promise<{ sim_run_id: string }> {
  return alertFetch("/alerts/utils/sim-run-id", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function evaluateRestorationCommitted(
  sessionId: string,
  body: {
    sim_run_id: string;
    initial_snapshot: Record<string, unknown>;
    group_restoration_times: Record<string, number | null>;
    modeled_group_id?: string;
  },
): Promise<{ created_events: unknown[]; session: AlertSessionResponse }> {
  return alertFetch(
    `/alerts/session/${encodeURIComponent(sessionId)}/evaluate/restoration-committed`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

export function evaluateRestorationPlayback(
  sessionId: string,
  body: {
    sim_run_id: string;
    playback_time_hours: number;
    modeled_group_id?: string;
    timeline: Record<string, unknown>[];
  },
): Promise<{ created: boolean; session: AlertSessionResponse }> {
  return alertFetch(
    `/alerts/session/${encodeURIComponent(sessionId)}/evaluate/restoration-playback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

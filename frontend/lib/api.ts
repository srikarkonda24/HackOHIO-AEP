import { API_BASE } from "./constants";
import type { CustomerNetworkContext } from "./networkContextTypes";
import type {
  RiskAssessmentResponse,
  RiskWeatherInputs,
} from "./riskAssessmentTypes";
import type {
  AssistantChatRequest,
  AssistantChatResponse,
  AssistantStatusResponse,
} from "./assistantTypes";
import type {
  RestorationNetworkResponse,
  RestorationSimRequest,
  RestorationSimResponse,
} from "./restorationTypes";
import type {
  DeviceImpactResponse,
  DeviceSearchResponse,
  DeviceUnavailableScenario,
  GisCatalogResponse,
  GisFeatureCollection,
  GisLocationMatch,
  HealthResponse,
  PremiseUpstreamResponse,
  DemoSectionConfig,
  StudyAreaConfig,
} from "./types";

function parseApiErrorDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);
    return parts.length ? parts.join("; ") : null;
  }
  return null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(
      "Cannot reach the GridAware API. Is FastAPI running on port 8000?",
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      const parsed = parseApiErrorDetail(body.detail);
      if (parsed) detail = parsed;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

export function searchDevices(
  q: string,
  limit = 20,
): Promise<DeviceSearchResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return fetchJson(`${API_BASE}/devices/search?${params}`);
}

export function getDeviceImpact(
  deviceKey: string,
  limit: number,
): Promise<DeviceImpactResponse> {
  const params = new URLSearchParams({
    device_key: deviceKey,
    limit: String(limit),
  });
  return fetchJson(`${API_BASE}/devices/impact?${params}`);
}

export function getPremiseUpstream(
  premiseId: string,
): Promise<PremiseUpstreamResponse> {
  return fetchJson(
    `${API_BASE}/premises/${encodeURIComponent(premiseId)}/upstream`,
  );
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJson(`${API_BASE}/health`);
}

export function getGisCatalog(): Promise<GisCatalogResponse> {
  return fetchJson(`${API_BASE}/gis/catalog`);
}

export function getGisStudyArea(): Promise<StudyAreaConfig> {
  return fetchJson(`${API_BASE}/gis/study-area`);
}

export function getGisDemoSection(): Promise<DemoSectionConfig> {
  return fetchJson(`${API_BASE}/gis/demo-section`);
}

export function getGisFeatures(args: {
  layer: string;
  bbox?: string;
  zoom?: number;
  limit?: number;
  circuit?: string;
  demoSection?: boolean;
}): Promise<GisFeatureCollection> {
  const params = new URLSearchParams({ layer: args.layer });
  if (args.bbox) params.set("bbox", args.bbox);
  if (args.zoom !== undefined) params.set("zoom", String(args.zoom));
  if (args.limit !== undefined) params.set("limit", String(args.limit));
  if (args.circuit) params.set("circuit", args.circuit);
  if (args.demoSection) params.set("demo_section", "true");
  return fetchJson(`${API_BASE}/gis/features?${params}`);
}

export function getGisLocation(locationId: string): Promise<GisLocationMatch> {
  return fetchJson(
    `${API_BASE}/gis/location/${encodeURIComponent(locationId)}`,
  );
}

export function getDeviceUnavailableScenario(
  deviceKey: string,
): Promise<DeviceUnavailableScenario> {
  const params = new URLSearchParams({ device_key: deviceKey });
  return fetchJson(`${API_BASE}/scenarios/device-unavailable?${params}`);
}

export function getCustomerNetworkContext(
  premiseId: string,
): Promise<CustomerNetworkContext> {
  return fetchJson(
    `${API_BASE}/customers/${encodeURIComponent(premiseId.trim())}/network-context`,
  );
}

export function getRestorationNetwork(): Promise<RestorationNetworkResponse> {
  return fetchJson(`${API_BASE}/restoration/network`);
}

export function postRestorationSimulate(
  body: RestorationSimRequest,
): Promise<RestorationSimResponse> {
  return fetchJson(`${API_BASE}/restoration/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface RestorationOutagePreviewResponse {
  damaged_component_ids: string[];
  snapshot: {
    simulated_outage_group_ids: string[];
    powered_group_ids: string[];
    switch_states?: Record<string, string>;
  };
}

export function postRestorationOutagePreview(body: {
  damaged_component_ids: string[];
}): Promise<RestorationOutagePreviewResponse> {
  return fetchJson(`${API_BASE}/restoration/outage-preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function postCustomerRiskAssessment(
  premiseId: string,
  inputs: RiskWeatherInputs,
): Promise<RiskAssessmentResponse> {
  return fetchJson(
    `${API_BASE}/customers/${encodeURIComponent(premiseId.trim())}/risk-assessment`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(inputs),
    },
  );
}

export function getAssistantStatus(): Promise<AssistantStatusResponse> {
  return fetchJson(`${API_BASE}/assistant/status`);
}

export function postAssistantChat(
  body: AssistantChatRequest,
): Promise<AssistantChatResponse> {
  return fetchJson(`${API_BASE}/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

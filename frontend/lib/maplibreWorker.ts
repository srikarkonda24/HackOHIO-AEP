import { setWorkerUrl } from "maplibre-gl";

/** Same-origin path served from frontend/public/maplibre/. */
export const MAPLIBRE_WORKER_URL = "/maplibre/maplibre-gl-worker.mjs";

let configured = false;

function isJavaScriptContentType(contentType: string | null): boolean {
  if (!contentType) return false;
  const type = contentType.toLowerCase();
  return (
    type.includes("javascript") ||
    type.includes("ecmascript") ||
    type.includes("application/octet-stream") ||
    type.startsWith("text/plain")
  );
}

/**
 * Point MapLibre at a locally served worker before `new Map()`.
 * Turbopack's default sibling-URL lookup returns HTML and fails with
 * "Worker failed to load. Check that the worker URL is correct."
 */
export async function configureMapLibreWorker(): Promise<string> {
  const response = await fetch(MAPLIBRE_WORKER_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(
      `MapLibre worker returned HTTP ${response.status} at ${MAPLIBRE_WORKER_URL}. Run npm run copy-maplibre-worker, then restart the Next.js server.`,
    );
  }

  const contentType = response.headers.get("content-type");
  const preview = (await response.text()).slice(0, 80);
  if (
    !isJavaScriptContentType(contentType) ||
    preview.trimStart().startsWith("<")
  ) {
    throw new Error(
      `MapLibre worker URL returned ${contentType ?? "unknown type"} instead of JavaScript. The worker must be a same-origin .mjs file, not an HTML page.`,
    );
  }

  if (!configured) {
    setWorkerUrl(MAPLIBRE_WORKER_URL);
    configured = true;
  }

  return MAPLIBRE_WORKER_URL;
}

/**
 * Copy MapLibre's official worker next to public/ so Next.js/Turbopack
 * does not derive a broken worker URL from the bundled import.meta.url.
 */
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const dist = path.join(
  path.dirname(require.resolve("maplibre-gl/package.json")),
  "dist",
);
const dest = path.join(process.cwd(), "public", "maplibre");

mkdirSync(dest, { recursive: true });
copyFileSync(
  path.join(dist, "maplibre-gl-worker.mjs"),
  path.join(dest, "maplibre-gl-worker.mjs"),
);
console.log("Copied MapLibre worker to public/maplibre/maplibre-gl-worker.mjs");

import type { Map as MaplibreMap } from "maplibre-gl";
import {
  GIS_LAYER_ORDER,
  GIS_LAYER_STYLE,
  renderLayerId,
  sourceId,
  type GisLayerId,
} from "@/lib/gisStyle";

const CUSTOMER_LAYER_IDS = ["clusters", "cluster-count", "unclustered-point"];

const LAYER_MIN_ZOOM: Partial<Record<GisLayerId, number>> = {
  primary: 10,
  reclosers: 10,
  switches: 11,
  fuses: 13,
  transformers: 13,
  poles: 14,
  secondary: 13,
  damage: 10,
  emergency: 10,
};

const LAYER_OPACITY: Partial<Record<GisLayerId, number>> = {
  primary: 0.75,
  reclosers: 0.72,
  switches: 0.68,
  fuses: 0.55,
  transformers: 0.55,
  poles: 0.45,
  secondary: 0.5,
  damage: 0.65,
  emergency: 0.7,
};

export function installGisLayers(map: MaplibreMap) {
  for (const layerId of GIS_LAYER_ORDER) {
    const sid = sourceId(layerId);
    const lid = renderLayerId(layerId);
    if (map.getSource(sid)) continue;

    map.addSource(sid, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });

    const style = GIS_LAYER_STYLE[layerId];
    const minzoom = LAYER_MIN_ZOOM[layerId] ?? 10;
    const opacity = LAYER_OPACITY[layerId] ?? 0.75;
    if (style.kind === "line") {
      map.addLayer({
        id: lid,
        type: "line",
        source: sid,
        minzoom,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": style.color,
          "line-width": style.width ?? 1.4,
          "line-opacity": opacity,
        },
      });
    } else {
      map.addLayer({
        id: lid,
        type: "circle",
        source: sid,
        minzoom,
        paint: {
          "circle-color": style.color,
          "circle-radius": style.radius ?? 4,
          "circle-opacity": opacity,
          "circle-stroke-width": [
            "case",
            ["==", ["get", "_topology_match"], true],
            1.2,
            0.4,
          ],
          "circle-stroke-color": [
            "case",
            ["==", ["get", "_topology_match"], true],
            "#e2e8f0",
            "#27272a",
          ],
        },
      });
    }
  }

  if (!map.getSource("gis-highlight")) {
    map.addSource("gis-highlight", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "gis-highlight-line",
      type: "line",
      source: "gis-highlight",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: {
        "line-color": "#fbbf24",
        "line-width": 4,
        "line-opacity": 0.95,
      },
    });
    map.addLayer({
      id: "gis-highlight-point",
      type: "circle",
      source: "gis-highlight",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 10,
        "circle-color": "rgba(251, 191, 36, 0.15)",
        "circle-stroke-width": 3,
        "circle-stroke-color": "#fbbf24",
      },
    });
  }

  // Keep customer clusters above infrastructure.
  for (const id of CUSTOMER_LAYER_IDS) {
    if (map.getLayer(id)) {
      map.moveLayer(id);
    }
  }
}

export function setGisLayerVisibility(
  map: MaplibreMap,
  visibility: Record<string, boolean>,
) {
  for (const layerId of GIS_LAYER_ORDER) {
    const lid = renderLayerId(layerId);
    if (!map.getLayer(lid)) continue;
    map.setLayoutProperty(
      lid,
      "visibility",
      visibility[layerId] === false ? "none" : "visible",
    );
  }
}

export function gisRenderLayerIds(): string[] {
  return GIS_LAYER_ORDER.map((id) => renderLayerId(id));
}

export function layerIdFromRenderLayer(renderId: string): GisLayerId | null {
  const prefix = "gis-";
  const suffix = "-render";
  if (!renderId.startsWith(prefix) || !renderId.endsWith(suffix)) return null;
  return renderId.slice(prefix.length, -suffix.length) as GisLayerId;
}

"use client";

import { useEffect, useRef, useState } from "react";
import {
  GeoJSONSource,
  Map,
  NavigationControl,
  type Map as MaplibreMap,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { CustomerPoint } from "@/lib/types";
import { customersToFeatureCollection } from "@/lib/geojson";
import { getGisFeatures } from "@/lib/api";
import {
  GIS_CLICK_PRIORITY,
  GIS_LAYER_ORDER,
  renderLayerId,
  sourceId,
} from "@/lib/gisStyle";
import { CARTO_FONT_STACK, MAP_STYLE_URLS } from "@/lib/mapStyles";
import { configureMapLibreWorker } from "@/lib/maplibreWorker";
import type {
  DemoSectionConfig,
  GisLayerMeta,
  SelectedGisAsset,
} from "@/lib/types";
import {
  gisRenderLayerIds,
  installGisLayers,
  layerIdFromRenderLayer,
  setGisLayerVisibility,
} from "./installGisLayers";

const SCENARIO_SOURCE_ID = "scenario-exposure";

function installScenarioLayers(map: MaplibreMap) {
  if (map.getSource(SCENARIO_SOURCE_ID)) return;

  map.addSource(SCENARIO_SOURCE_ID, {
    type: "geojson",
    data: { type: "FeatureCollection", features: [] },
    cluster: true,
    clusterMaxZoom: 14,
    clusterRadius: 50,
  });

  map.addLayer({
    id: "scenario-clusters",
    type: "circle",
    source: SCENARIO_SOURCE_ID,
    filter: ["has", "point_count"],
    paint: {
      "circle-color": [
        "step",
        ["get", "point_count"],
        "#e879f9",
        50,
        "#d946ef",
        200,
        "#c026d3",
        1000,
        "#a21caf",
      ],
      "circle-radius": [
        "step",
        ["get", "point_count"],
        20,
        50,
        24,
        200,
        30,
        1000,
        36,
      ],
      "circle-opacity": 0.92,
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fdf4ff",
    },
  });

  map.addLayer({
    id: "scenario-cluster-count",
    type: "symbol",
    source: SCENARIO_SOURCE_ID,
    filter: ["has", "point_count"],
    layout: {
      "text-field": ["get", "point_count_abbreviated"],
      "text-font": [...CARTO_FONT_STACK],
      "text-size": 12,
    },
    paint: { "text-color": "#fdf4ff" },
  });

  map.addLayer({
    id: "scenario-unclustered-point",
    type: "circle",
    source: SCENARIO_SOURCE_ID,
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-color": "#f0abfc",
      "circle-radius": 6,
      "circle-stroke-width": 2,
      "circle-stroke-color": "#fdf4ff",
    },
  });
}

type MapStatus = "initializing" | "ready" | "error";

interface ImpactMapProps {
  catalog?: GisLayerMeta[];
  layerVisibility?: Record<string, boolean>;
  selectedAsset?: SelectedGisAsset | null;
  onGisAssetClick?: (asset: SelectedGisAsset) => void;
  scenarioCustomers?: CustomerPoint[] | null;
  impactLoading?: boolean;
  demoSection?: DemoSectionConfig | null;
}

export function ImpactMap({
  catalog = [],
  layerVisibility = {},
  selectedAsset,
  onGisAssetClick,
  scenarioCustomers = null,
  impactLoading = false,
  demoSection = null,
}: ImpactMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const layersReadyRef = useRef(false);
  const styleIndexRef = useRef(0);
  const onGisAssetClickRef = useRef(onGisAssetClick);
  onGisAssetClickRef.current = onGisAssetClick;
  const visibilityRef = useRef(layerVisibility);
  visibilityRef.current = layerVisibility;
  const catalogRef = useRef(catalog);
  catalogRef.current = catalog;
  const demoSectionRef = useRef(demoSection);
  demoSectionRef.current = demoSection;
  const demoFitDoneRef = useRef(false);

  const [mapStatus, setMapStatus] = useState<MapStatus>("initializing");
  const [mapError, setMapError] = useState<string | null>(null);

  const applyScenarioData = (map: MaplibreMap, points: CustomerPoint[]) => {
    if (!layersReadyRef.current) return;
    const source = map.getSource(SCENARIO_SOURCE_ID) as GeoJSONSource | undefined;
    if (!source) return;
    const collection = customersToFeatureCollection(points);
    source.setData(collection);
    map.resize();
  };

  const applyDemoMapConstraints = (map: MaplibreMap) => {
    const section = demoSectionRef.current;
    if (!section?.bounds_wgs84) return;
    const b = section.bounds_wgs84;
    const pad = section.map?.max_bounds_padding ?? 0.002;
    map.setMaxBounds([
      [b.min_lng - pad, b.min_lat - pad],
      [b.max_lng + pad, b.max_lat + pad],
    ]);
    if (section.map?.min_zoom != null) {
      map.setMinZoom(section.map.min_zoom);
    }
    if (section.map?.max_zoom != null) {
      map.setMaxZoom(section.map.max_zoom);
    }
    map.fitBounds(
      [
        [b.min_lng, b.min_lat],
        [b.max_lng, b.max_lat],
      ],
      {
        padding: 36,
        duration: 0,
        maxZoom: section.map?.max_zoom ?? 16,
      },
    );
  };

  const refreshGisLayers = async (map: MaplibreMap) => {
    const bounds = map.getBounds();
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
    const zoom = map.getZoom();
    const visibility = visibilityRef.current;
    const metaById = Object.fromEntries(
      catalogRef.current.map((layer) => [layer.layer_id, layer]),
    );
    const useDemoSection = Boolean(demoSectionRef.current);

    await Promise.all(
      GIS_LAYER_ORDER.map(async (layerId) => {
        if (visibility[layerId] === false) return;
        const meta = metaById[layerId];
        const source = map.getSource(sourceId(layerId)) as
          | GeoJSONSource
          | undefined;
        if (!source) return;
        if (meta && zoom < meta.min_zoom) {
          source.setData({ type: "FeatureCollection", features: [] });
          return;
        }
        try {
          const data = await getGisFeatures({
            layer: layerId,
            bbox:
              useDemoSection || meta?.bbox_required === false ? undefined : bbox,
            demoSection: useDemoSection,
            zoom,
            limit: 5000,
          });
          source.setData(data as unknown as GeoJSON.FeatureCollection);
        } catch {
          /* keep previous layer data if a refresh fails */
        }
      }),
    );
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container || mapRef.current) return;

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    layersReadyRef.current = false;
    styleIndexRef.current = 0;

    const finishMapReady = (map: MaplibreMap) => {
      if (cancelled || !map.isStyleLoaded()) return;
      try {
        installScenarioLayers(map);
        installGisLayers(map);
        setGisLayerVisibility(map, visibilityRef.current);
        layersReadyRef.current = true;
        setMapStatus("ready");
        setMapError(null);
        if (demoSectionRef.current && !demoFitDoneRef.current) {
          applyDemoMapConstraints(map);
          demoFitDoneRef.current = true;
        }
        void refreshGisLayers(map);
        map.resize();
      } catch (err) {
        layersReadyRef.current = false;
        setMapStatus("error");
        setMapError(
          err instanceof Error ? err.message : "Failed to add map layers",
        );
      }
    };

    const tryFallbackStyle = (map: MaplibreMap) => {
      const next = styleIndexRef.current + 1;
      if (next >= MAP_STYLE_URLS.length) {
        setMapStatus("error");
        setMapError(
          "Basemap failed to load. Check network access to CARTO or MapLibre demo tiles.",
        );
        return;
      }
      styleIndexRef.current = next;
      layersReadyRef.current = false;
      setMapStatus("initializing");
      setMapError(null);
      map.setStyle(MAP_STYLE_URLS[next]);
    };

    const attachMapHandlers = (map: MaplibreMap) => {
      map.addControl(new NavigationControl(), "top-right");

      map.on("load", () => finishMapReady(map));
      map.on("styledata", () => {
        if (map.isStyleLoaded() && !layersReadyRef.current) {
          finishMapReady(map);
        }
      });

      map.on("error", (event) => {
        const message =
          event.error?.message ??
          (typeof event.error === "string" ? event.error : null);
        if (!message || cancelled) return;
        if (message.includes("Worker failed to load")) {
          setMapStatus("error");
          setMapError(
            "MapLibre worker failed to load. Confirm /maplibre/maplibre-gl-worker.mjs is served as JavaScript.",
          );
          return;
        }
        if (
          message.includes("Failed to load") ||
          message.includes("404") ||
          message.includes("style") ||
          message.includes("Sprite") ||
          message.includes("glyphs")
        ) {
          tryFallbackStyle(map);
        }
      });

      map.on("click", "scenario-clusters", (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["scenario-clusters"],
        });
        const clusterId = features[0]?.properties?.cluster_id;
        if (clusterId === undefined) return;
        const source = map.getSource(SCENARIO_SOURCE_ID) as GeoJSONSource;
        void source.getClusterExpansionZoom(clusterId).then((zoom) => {
          const geometry = features[0].geometry;
          if (geometry.type !== "Point") return;
          map.easeTo({
            center: geometry.coordinates as [number, number],
            zoom,
          });
        });
      });

      map.on("click", (e) => {
        const exposureHits = map.queryRenderedFeatures(e.point, {
          layers: [
            "scenario-clusters",
            "scenario-unclustered-point",
          ].filter((id) => map.getLayer(id)),
        });
        if (exposureHits.length > 0) return;
        const hits = map.queryRenderedFeatures(e.point, {
          layers: gisRenderLayerIds().filter((id) => map.getLayer(id)),
        });
        if (hits.length === 0) return;
        const ranked = [...hits].sort((a, b) => {
          const ai = GIS_CLICK_PRIORITY.indexOf(
            layerIdFromRenderLayer(a.layer.id) ?? "poles",
          );
          const bi = GIS_CLICK_PRIORITY.indexOf(
            layerIdFromRenderLayer(b.layer.id) ?? "poles",
          );
          return ai - bi;
        });
        const hit = ranked[0];
        const layerId = layerIdFromRenderLayer(hit.layer.id);
        const props = hit.properties as Record<string, unknown> | undefined;
        if (!layerId || !props || !onGisAssetClickRef.current) return;
        onGisAssetClickRef.current({
          layerId,
          featureId: String(props._feature_id ?? ""),
          locationId: props._location_n ? String(props._location_n) : null,
          properties: props as SelectedGisAsset["properties"],
          geometry: hit.geometry as SelectedGisAsset["geometry"],
        });
      });

      for (const layerId of GIS_LAYER_ORDER) {
        const lid = renderLayerId(layerId);
        map.on("mouseenter", lid, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", lid, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      let moveTimer: number | null = null;
      const scheduleGisRefresh = () => {
        if (moveTimer) window.clearTimeout(moveTimer);
        moveTimer = window.setTimeout(() => {
          if (layersReadyRef.current) void refreshGisLayers(map);
        }, 280);
      };
      map.on("moveend", scheduleGisRefresh);
      map.on("zoomend", scheduleGisRefresh);

      for (const layer of [
        "scenario-clusters",
        "scenario-unclustered-point",
      ] as const) {
        map.on("mouseenter", layer, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layer, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      for (const id of [
        "scenario-clusters",
        "scenario-cluster-count",
        "scenario-unclustered-point",
      ]) {
        if (map.getLayer(id)) map.moveLayer(id);
      }
    };

    void (async () => {
      try {
        await configureMapLibreWorker();
      } catch (err) {
        if (!cancelled) {
          setMapStatus("error");
          setMapError(
            err instanceof Error
              ? err.message
              : "Failed to configure the MapLibre worker",
          );
        }
        return;
      }

      if (cancelled || !containerRef.current) return;

      try {
        const map = new Map({
          container: containerRef.current,
          style: MAP_STYLE_URLS[0],
          center: [-79.85, 37.28],
          zoom: 10,
          attributionControl: { compact: true },
        });

        attachMapHandlers(map);
        mapRef.current = map;

        resizeObserver = new ResizeObserver(() => {
          map.resize();
        });
        resizeObserver.observe(containerRef.current);
        requestAnimationFrame(() => map.resize());
      } catch (err) {
        if (!cancelled) {
          setMapStatus("error");
          setMapError(
            err instanceof Error ? err.message : "Failed to create the map",
          );
        }
      }
    })();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      mapRef.current?.remove();
      mapRef.current = null;
      layersReadyRef.current = false;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layersReadyRef.current) return;
    if (!scenarioCustomers || scenarioCustomers.length === 0) {
      const source = map.getSource(SCENARIO_SOURCE_ID) as GeoJSONSource | undefined;
      source?.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    applyScenarioData(map, scenarioCustomers);
  }, [scenarioCustomers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layersReadyRef.current) return;
    setGisLayerVisibility(map, layerVisibility);
    void refreshGisLayers(map);
  }, [layerVisibility, catalog, demoSection]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layersReadyRef.current || !demoSection) return;
    applyDemoMapConstraints(map);
    void refreshGisLayers(map);
  }, [demoSection]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !layersReadyRef.current) return;
    const source = map.getSource("gis-highlight") as GeoJSONSource | undefined;
    if (!source) return;
    if (!selectedAsset?.geometry) {
      source.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    source.setData({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: selectedAsset.geometry as GeoJSON.Geometry,
          properties: {},
        },
      ],
    });
  }, [selectedAsset]);

  return (
    <div className="relative h-full min-h-[280px] w-full flex-1 bg-zinc-800">
      <div
        ref={containerRef}
        className="absolute inset-0 min-h-[280px] w-full"
        aria-label="Equipment and exposure map"
      />

      {mapStatus === "initializing" ? (
        <div className="pointer-events-none absolute inset-0 z-[5] flex items-center justify-center bg-zinc-900/40">
          <p className="rounded-md bg-zinc-900/90 px-4 py-2 text-sm text-zinc-300 ring-1 ring-zinc-700">
            Loading basemap…
          </p>
        </div>
      ) : null}

      {mapStatus === "error" && mapError ? (
        <div
          className="absolute inset-0 z-[20] flex items-center justify-center bg-zinc-950/90 p-6"
          role="alert"
        >
          <div className="max-w-md rounded-lg border border-red-900/50 bg-zinc-900 p-4 text-center">
            <p className="text-sm font-medium text-red-300">Map unavailable</p>
            <p className="mt-2 text-sm text-zinc-400">{mapError}</p>
            {mapError.toLowerCase().includes("worker") ? (
              <p className="mt-2 text-xs text-zinc-600">
                Expected worker: /maplibre/maplibre-gl-worker.mjs
              </p>
            ) : (
              <p className="mt-2 text-xs text-zinc-600">
                Tried basemaps: {MAP_STYLE_URLS.join(" → ")}
              </p>
            )}
          </div>
        </div>
      ) : null}

      {impactLoading ? (
        <div className="pointer-events-none absolute inset-0 z-[5] flex items-center justify-center bg-zinc-950/25">
          <p className="rounded-md bg-zinc-900/90 px-4 py-2 text-sm text-zinc-300 ring-1 ring-zinc-700">
            Calculating modeled exposure…
          </p>
        </div>
      ) : null}

      <div className="pointer-events-none absolute bottom-4 left-4 z-10 rounded-md border border-zinc-700/80 bg-zinc-950/90 px-3 py-2 text-[11px] text-zinc-400 shadow-lg">
        <ul className="space-y-1">
          <li className="flex items-center gap-2">
            <span className="h-0.5 w-4 bg-yellow-400" />
            GIS primary (local circuit)
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
            Recloser
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-fuchsia-400" />
            Modeled exposure
          </li>
        </ul>
      </div>
    </div>
  );
}

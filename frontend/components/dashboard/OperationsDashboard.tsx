"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { DashboardLayout } from "./DashboardLayout";
import {
  EquipmentContextPanel,
  type SelectedTopologyDevice,
} from "@/components/equipment/EquipmentContextPanel";
import {
  ApiError,
  getDeviceUnavailableScenario,
  getGisCatalog,
  getGisLocation,
  getGisDemoSection,
  getHealth,
} from "@/lib/api";
import { DEFAULT_LAYER_VISIBILITY } from "@/lib/constants";
import { clearGisSelectionState } from "@/lib/topologyDeviceSelection";
import type {
  ActiveExposureScenario,
  DemoSectionConfig,
  DemoSectionDevice,
  GisLayerMeta,
  GisLocationMatch,
  SelectedGisAsset,
  TopologyDeviceMatch,
} from "@/lib/types";

const ImpactMap = dynamic(
  () => import("@/components/map/ImpactMap").then((m) => m.ImpactMap),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[280px] items-center justify-center bg-zinc-800 text-sm text-zinc-500">
        Loading map…
      </div>
    ),
  },
);

function deviceFromMatch(device: TopologyDeviceMatch): SelectedTopologyDevice {
  return {
    deviceKey: device.device_key,
    deviceType: device.device_type,
    locationId: device.location_id,
  };
}

export function OperationsDashboard() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [catalog, setCatalog] = useState<GisLayerMeta[]>([]);
  const [demoSection, setDemoSection] = useState<DemoSectionConfig | null>(null);
  const [layerVisibility] = useState<Record<string, boolean>>(
    () => ({ ...DEFAULT_LAYER_VISIBILITY }),
  );

  const [selectedDevice, setSelectedDevice] =
    useState<SelectedTopologyDevice | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<SelectedGisAsset | null>(
    null,
  );
  const [locationMatch, setLocationMatch] = useState<GisLocationMatch | null>(
    null,
  );
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const [activeScenario, setActiveScenario] =
    useState<ActiveExposureScenario | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [impactError, setImpactError] = useState<string | null>(null);

  const scenarioCustomers = activeScenario?.data.customers ?? null;
  const impactCount = activeScenario
    ? activeScenario.data.modeled_potential_exposure_count
    : null;

  const exposurePointsOutsideBounds = (() => {
    if (!demoSection || !scenarioCustomers?.length) return null;
    const b = demoSection.bounds_wgs84;
    let outside = 0;
    for (const c of scenarioCustomers) {
      if (
        c.longitude < b.min_lng ||
        c.longitude > b.max_lng ||
        c.latitude < b.min_lat ||
        c.latitude > b.max_lat
      ) {
        outside += 1;
      }
    }
    return outside;
  })();

  useEffect(() => {
    getHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
    getGisCatalog()
      .then((data) => setCatalog(data.layers))
      .catch(() => {});
    getGisDemoSection()
      .then(setDemoSection)
      .catch(() => {});
  }, []);

  const clearGisSelection = useCallback(() => {
    const cleared = clearGisSelectionState();
    setSelectedAsset(cleared.selectedAsset);
    setLocationMatch(cleared.locationMatch);
    setMatchError(cleared.matchError);
    setMatchLoading(cleared.matchLoading);
  }, []);

  const clearImpact = useCallback(() => {
    setActiveScenario(null);
    setImpactError(null);
  }, []);

  const runImpactAnalysis = useCallback(
    async (deviceKey: string, gis?: SelectedGisAsset | null) => {
      setImpactLoading(true);
      setImpactError(null);
      try {
        const data = await getDeviceUnavailableScenario(deviceKey);
        setActiveScenario({
          deviceKey,
          gisLayerId: gis?.layerId,
          gisFeatureId: gis?.featureId,
          locationId: gis?.locationId,
          data,
        });
      } catch (e) {
        setActiveScenario(null);
        setImpactError(
          e instanceof ApiError ? e.message : "Failed to calculate exposure",
        );
      } finally {
        setImpactLoading(false);
      }
    },
    [],
  );

  const handleSelectDemoDevice = useCallback(
    (device: DemoSectionDevice) => {
      clearImpact();
      clearGisSelection();
      setSelectedDevice({
        deviceKey: device.device_key,
        deviceType: device.device_type,
        locationId: device.location_n,
      });
    },
    [clearGisSelection, clearImpact],
  );

  const handlePickTopologyDevice = useCallback(
    (device: TopologyDeviceMatch) => {
      clearImpact();
      setSelectedDevice(deviceFromMatch(device));
    },
    [clearImpact],
  );

  const handleShowPotentialImpact = useCallback(() => {
    if (!selectedDevice) return;
    void runImpactAnalysis(selectedDevice.deviceKey, selectedAsset);
  }, [selectedDevice, selectedAsset, runImpactAnalysis]);

  const handleGisAssetClick = useCallback(
    async (asset: SelectedGisAsset) => {
      clearImpact();
      setSelectedDevice(null);
      setSelectedAsset(asset);
      setLocationMatch(null);
      setMatchError(null);

      if (asset.layerId === "damage" || asset.layerId === "emergency") {
        setMatchLoading(false);
        return;
      }
      if (!asset.locationId) {
        setMatchLoading(false);
        return;
      }
      setMatchLoading(true);
      try {
        const data = await getGisLocation(asset.locationId);
        setLocationMatch(data);
        if (data.devices.length === 1) {
          setSelectedDevice(deviceFromMatch(data.devices[0]));
        }
      } catch (e) {
        setMatchError(
          e instanceof ApiError ? e.message : "Failed to look up location join",
        );
      } finally {
        setMatchLoading(false);
      }
    },
    [clearImpact],
  );

  return (
    <DashboardLayout
      header={
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/15 ring-1 ring-amber-500/40">
              <span className="text-xs font-bold text-amber-400">GA</span>
            </div>
            <h1 className="text-base font-semibold text-zinc-50">GridAware Operations</h1>
            <Link href="/prediction" className="ml-2 text-xs text-zinc-500 hover:text-zinc-300">
              ← Concierge
            </Link>
          </div>
          <span
            className={`text-xs ${
              apiOnline === false
                ? "text-red-400"
                : apiOnline
                  ? "text-emerald-500"
                  : "text-zinc-600"
            }`}
          >
            {apiOnline === false
              ? "Offline"
              : apiOnline
                ? "Connected"
                : "…"}
          </span>
        </div>
      }
      map={
        <ImpactMap
          catalog={catalog}
          layerVisibility={layerVisibility}
          selectedAsset={selectedAsset}
          onGisAssetClick={handleGisAssetClick}
          scenarioCustomers={scenarioCustomers}
          impactLoading={impactLoading}
          demoSection={demoSection}
        />
      }
      panel={
        <EquipmentContextPanel
          demoSection={demoSection}
          selectedDevice={selectedDevice}
          selectedAsset={selectedAsset}
          locationMatch={locationMatch}
          matchLoading={matchLoading}
          matchError={matchError}
          onSelectDemoDevice={handleSelectDemoDevice}
          onPickTopologyDevice={handlePickTopologyDevice}
          onShowPotentialImpact={handleShowPotentialImpact}
          onClearImpact={clearImpact}
          impactLoading={impactLoading}
          impactCount={impactCount}
          impactError={impactError}
          impactActive={Boolean(activeScenario)}
          apiOffline={apiOnline === false}
          exposurePointsOutsideBounds={exposurePointsOutsideBounds}
        />
      }
    />
  );
}

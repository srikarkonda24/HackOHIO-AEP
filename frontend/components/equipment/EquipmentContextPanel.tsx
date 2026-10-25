"use client";

import type {
  DemoSectionConfig,
  DemoSectionDevice,
  GisLocationMatch,
  SelectedGisAsset,
  TopologyDeviceMatch,
} from "@/lib/types";

export interface SelectedTopologyDevice {
  deviceKey: string;
  deviceType: string;
  locationId: string;
}

interface EquipmentContextPanelProps {
  selectedDevice: SelectedTopologyDevice | null;
  selectedAsset: SelectedGisAsset | null;
  locationMatch: GisLocationMatch | null;
  matchLoading: boolean;
  matchError: string | null;
  onSelectDemoDevice: (device: DemoSectionDevice) => void;
  onPickTopologyDevice: (device: TopologyDeviceMatch) => void;
  onShowPotentialImpact: () => void;
  onClearImpact: () => void;
  impactLoading: boolean;
  impactCount: number | null;
  impactError: string | null;
  impactActive: boolean;
  apiOffline: boolean;
  demoSection?: DemoSectionConfig | null;
  exposurePointsOutsideBounds?: number | null;
}

export function EquipmentContextPanel({
  selectedDevice,
  selectedAsset,
  locationMatch,
  matchLoading,
  matchError,
  onSelectDemoDevice,
  onPickTopologyDevice,
  onShowPotentialImpact,
  onClearImpact,
  impactLoading,
  impactCount,
  impactError,
  impactActive,
  apiOffline,
  demoSection = null,
  exposurePointsOutsideBounds = null,
}: EquipmentContextPanelProps) {
  const canAnalyze = selectedDevice != null;
  const devices = demoSection?.protective_devices ?? [];

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden text-sm">
      <div className="shrink-0 border-b border-zinc-800 px-4 py-3">
        <p className="font-semibold text-zinc-100">Exposure</p>
        {apiOffline ? (
          <p className="mt-1 text-xs text-red-400" role="alert">
            API offline
          </p>
        ) : null}
      </div>

      <div className="shrink-0 border-b border-zinc-800 px-4 py-3">
        <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
          Demo devices
        </p>
        <ul className="mt-2 space-y-1.5">
          {devices.map((device) => {
            const active = selectedDevice?.deviceKey === device.device_key;
            return (
              <li key={device.device_key}>
                <button
                  type="button"
                  disabled={apiOffline}
                  onClick={() => onSelectDemoDevice(device)}
                  className={`w-full rounded-md border px-2.5 py-2 text-left text-xs transition-colors ${
                    active
                      ? "border-amber-600/50 bg-amber-950/25 text-zinc-100"
                      : "border-zinc-700 text-zinc-300 hover:border-zinc-600 hover:bg-zinc-900/80"
                  }`}
                >
                  <span className="block text-zinc-200">{device.device_type}</span>
                  <span className="mt-0.5 block font-mono text-[10px] text-zinc-500">
                    {device.location_n}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {!devices.length ? (
          <p className="mt-2 text-xs text-zinc-500">Load demo section from API.</p>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-hidden px-4 py-3">
        {selectedDevice ? (
          <dl className="space-y-2 text-xs">
            <div>
              <dt className="text-zinc-600">Selected</dt>
              <dd className="text-zinc-200">{selectedDevice.deviceType}</dd>
            </div>
            <div>
              <dt className="text-zinc-600">Location</dt>
              <dd className="font-mono text-zinc-400">{selectedDevice.locationId}</dd>
            </div>
          </dl>
        ) : selectedAsset && matchLoading ? (
          <p className="text-xs text-zinc-500">Matching…</p>
        ) : selectedAsset && locationMatch && locationMatch.devices.length > 1 ? (
          <ul className="space-y-1.5">
            {locationMatch.devices.map((device) => (
              <li key={device.device_key}>
                <button
                  type="button"
                  onClick={() => onPickTopologyDevice(device)}
                  className="w-full rounded-md border border-zinc-700 px-2 py-1.5 text-left text-xs hover:bg-zinc-900"
                >
                  {device.device_type}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-zinc-500">Pick a device or map marker.</p>
        )}

        {matchError ? (
          <p className="mt-2 text-xs text-red-400">{matchError}</p>
        ) : null}

        {canAnalyze && !impactActive ? (
          <button
            type="button"
            disabled={impactLoading || apiOffline}
            onClick={onShowPotentialImpact}
            className="mt-3 w-full rounded-md bg-fuchsia-700 px-3 py-2.5 text-sm font-medium text-white hover:bg-fuchsia-600 disabled:opacity-50"
          >
            {impactLoading ? "Calculating…" : "Calculate exposure"}
          </button>
        ) : null}

        {impactActive && impactCount != null ? (
          <div className="mt-3">
            <p className="text-[11px] uppercase tracking-wide text-zinc-500">
              Modeled exposure
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-fuchsia-200">
              {impactCount.toLocaleString()}
            </p>
            {exposurePointsOutsideBounds != null &&
            exposurePointsOutsideBounds > 0 ? (
              <p className="mt-1 text-[11px] leading-snug text-amber-200/80">
                {exposurePointsOutsideBounds.toLocaleString()} returned map points
                are outside this view.
              </p>
            ) : null}
            <button
              type="button"
              onClick={onClearImpact}
              className="mt-3 w-full rounded-md border border-zinc-600 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Clear
            </button>
          </div>
        ) : null}

        {impactError ? (
          <p className="mt-2 text-xs text-red-400" role="alert">
            {impactError}
          </p>
        ) : null}
      </div>
    </div>
  );
}

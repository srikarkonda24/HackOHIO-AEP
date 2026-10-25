"use client";

import type { GisLocationMatch, SelectedGisAsset, TopologyDeviceMatch } from "@/lib/types";

const DAMAGE_LABELS: Record<string, string> = {
  Inform_Wor: "Damage type",
  Asset_Type: "Asset type",
  Report_Tim: "Report date",
  Repaired_D: "Repaired date",
  Repaired: "Repaired",
  Circuit: "Circuit",
  Substation: "Substation",
  Event: "Event",
  Region: "Region",
  District: "District",
  Status: "Status",
  Access_Iss: "Access issue",
  Special_Eq: "Special equipment",
  Longitude: "Longitude",
  Latitude: "Latitude",
  Outage_Num: "Outage number",
};

const GENERIC_LABELS: Record<string, string> = {
  device_typ: "Device type",
  location_n: "Location identifier",
  circuit_id: "Circuit ID",
  aep_circui: "AEP circuit",
  aep_statio: "Substation",
  status: "Status",
  usage: "Usage",
  mounting: "Mounting",
  nominal_vo: "Nominal voltage",
  normal_sta: "Normal state",
  eo_source_: "Source type",
  owner_name: "Owner",
  material: "Material",
  height: "Height",
  class: "Class",
  aep_custom: "AEP customer count field",
  upstream_l: "Upstream location",
  NAME: "Name",
  ADDRESS: "Address",
  CITY: "City",
  STATE: "State",
  ZIPCODE: "ZIP",
  facility_kind: "Facility kind",
};

function labelFor(layerId: string, key: string): string {
  if (layerId === "damage" && DAMAGE_LABELS[key]) return DAMAGE_LABELS[key];
  return GENERIC_LABELS[key] ?? key;
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

interface AssetInspectPanelProps {
  asset: SelectedGisAsset | null;
  match: GisLocationMatch | null;
  matchLoading: boolean;
  matchError: string | null;
  onViewDependents: (deviceKey: string) => void;
  onSimulateUnavailable: (deviceKey: string) => void;
  simulateLoading: boolean;
  activeScenarioDeviceKey: string | null;
  onClear: () => void;
}

export function AssetInspectPanel({
  asset,
  match,
  matchLoading,
  matchError,
  onViewDependents,
  onSimulateUnavailable,
  simulateLoading,
  activeScenarioDeviceKey,
  onClear,
}: AssetInspectPanelProps) {
  if (!asset) return null;

  const canSimulate =
    asset.properties._topology_match === true &&
    asset.layerId !== "damage" &&
    asset.layerId !== "emergency";

  const hidden = new Set([
    "_layer",
    "_feature_id",
    "_location_n",
    "_topology_match",
  ]);
  const entries = Object.entries(asset.properties).filter(
    ([key, value]) => !hidden.has(key) && value !== "" && value !== null,
  );

  return (
    <div className="border-b border-zinc-800 p-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Selected map asset
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="text-[11px] text-zinc-500 hover:text-zinc-300"
        >
          Clear
        </button>
      </div>
      <p className="mt-1 text-sm text-zinc-100">
        {asset.properties.device_typ ||
          asset.properties.Inform_Wor ||
          asset.properties.NAME ||
          asset.layerId}
      </p>
      <p className="mt-0.5 font-mono text-[11px] text-zinc-500">
        {asset.layerId} · {asset.featureId}
      </p>

      <dl className="mt-3 max-h-48 space-y-2 overflow-y-auto text-xs">
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt className="uppercase tracking-wide text-zinc-600">
              {labelFor(asset.layerId, key)}
            </dt>
            <dd className="break-words text-zinc-200">{displayValue(value)}</dd>
          </div>
        ))}
      </dl>

      {asset.layerId === "damage" ? (
        <p className="mt-3 text-[11px] leading-relaxed text-zinc-600">
          ARCOS damage is a historical work record. It is not a verified
          customer outage label.
        </p>
      ) : null}

      {matchLoading ? (
        <p className="mt-3 text-xs text-zinc-500">Checking topology join…</p>
      ) : null}
      {matchError ? (
        <p className="mt-3 text-xs text-red-400">{matchError}</p>
      ) : null}

      {match ? (
        <div className="mt-3 rounded-md border border-zinc-800 bg-zinc-900/70 p-2">
          <p className="text-[11px] uppercase tracking-wide text-zinc-500">
            Exact location_id matches
          </p>
          {match.devices.length === 0 ? (
            <p className="mt-1 text-xs text-zinc-500">
              No network.db device uses this location identifier. Geographic
              nearness is not treated as a match.
            </p>
          ) : (
            <ul className="mt-1 space-y-2">
              {match.devices.map((device: TopologyDeviceMatch) => (
                <li key={device.device_key}>
                  <p className="text-xs text-zinc-200">{device.device_type}</p>
                  <p className="font-mono text-[10px] text-zinc-500">
                    {device.device_key}
                  </p>
                  <p className="text-[11px] text-zinc-400">
                    {device.dependent_premises.toLocaleString()} potentially
                    dependent premises
                  </p>
                  <button
                    type="button"
                    onClick={() => onViewDependents(device.device_key)}
                    className="mt-1 rounded border border-amber-700/50 px-2 py-1 text-[11px] text-amber-200 hover:bg-amber-500/10"
                  >
                    View potentially dependent premises
                  </button>
                  {canSimulate ? (
                    <button
                      type="button"
                      disabled={simulateLoading}
                      onClick={() => onSimulateUnavailable(device.device_key)}
                      className="mt-1 block w-full rounded border border-fuchsia-700/60 bg-fuchsia-950/40 px-2 py-1.5 text-[11px] font-medium text-fuchsia-200 hover:bg-fuchsia-900/40 disabled:opacity-50"
                    >
                      {simulateLoading &&
                      activeScenarioDeviceKey === device.device_key
                        ? "Running scenario…"
                        : "Simulate device unavailable"}
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

"use client";

import type { ActiveExposureScenario } from "@/lib/types";

interface ScenarioExposurePanelProps {
  scenario: ActiveExposureScenario;
  plottedCount: number;
  onClear: () => void;
}

export function ScenarioExposurePanel({
  scenario,
  plottedCount,
  onClear,
}: ScenarioExposurePanelProps) {
  const { data } = scenario;
  return (
    <div className="border-b border-fuchsia-900/40 bg-fuchsia-950/20 p-4">
      <div className="flex items-start justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-fuchsia-300">
          Simulated device unavailable
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="text-[11px] text-fuchsia-300/80 hover:text-fuchsia-200"
        >
          Clear scenario
        </button>
      </div>
      <p className="mt-2 text-sm text-zinc-100">{data.device.device_type}</p>
      <p className="font-mono text-[11px] text-zinc-500">{data.device_key}</p>
      {scenario.locationId ? (
        <p className="mt-1 font-mono text-[10px] text-zinc-600">
          GIS location {scenario.locationId}
          {scenario.gisLayerId ? ` · ${scenario.gisLayerId}` : ""}
        </p>
      ) : null}
      <dl className="mt-3 space-y-2 text-xs">
        <div>
          <dt className="uppercase text-zinc-500">
            Modeled potential exposure (premises)
          </dt>
          <dd className="text-2xl font-semibold tabular-nums text-fuchsia-200">
            {data.modeled_potential_exposure_count.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="uppercase text-zinc-500">Locations highlighted on map</dt>
          <dd className="tabular-nums text-zinc-200">
            {plottedCount.toLocaleString()}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-[11px] leading-relaxed text-zinc-500">
        {data.disclaimer}
      </p>
    </div>
  );
}

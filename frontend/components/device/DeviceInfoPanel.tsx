"use client";

import type { DeviceImpactResponse, PremiseUpstreamResponse } from "@/lib/types";

interface DeviceInfoPanelProps {
  impact: DeviceImpactResponse | null;
  loading: boolean;
  error: string | null;
  plottedCount: number;
  selectedPremiseId: string | null;
  upstream: PremiseUpstreamResponse | null;
  upstreamLoading: boolean;
  upstreamError: string | null;
  onClearPremise: () => void;
  onSimulateUnavailable?: (deviceKey: string) => void;
  simulateLoading?: boolean;
  activeScenarioDeviceKey?: string | null;
  scenarioActive?: boolean;
}

export function DeviceInfoPanel({
  impact,
  loading,
  error,
  plottedCount,
  selectedPremiseId,
  upstream,
  upstreamLoading,
  upstreamError,
  onClearPremise,
  onSimulateUnavailable,
  simulateLoading = false,
  activeScenarioDeviceKey = null,
  scenarioActive = false,
}: DeviceInfoPanelProps) {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Selected equipment
      </h2>

      {loading ? (
        <p className="mt-4 text-sm text-zinc-500">Loading impact data…</p>
      ) : null}

      {error ? (
        <p className="mt-4 text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {!loading && !error && !impact ? (
        <p className="mt-4 text-sm text-zinc-500">
          Search and select equipment to view dependency impact.
        </p>
      ) : null}

      {impact ? (
        <dl className="mt-4 space-y-3 text-sm">
          <div>
            <dt className="text-[11px] uppercase text-zinc-500">Device type</dt>
            <dd className="mt-0.5 text-zinc-100">{impact.device.device_type}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase text-zinc-500">
              Equipment identifier
            </dt>
            <dd className="mt-0.5 break-all font-mono text-xs text-amber-200/90">
              {impact.device.device_key}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase text-zinc-500">
              Location identifier
            </dt>
            <dd className="mt-0.5 font-mono text-xs text-zinc-300">
              {impact.device.location_id}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase text-zinc-500">
              Potentially dependent premises
            </dt>
            <dd className="mt-0.5 text-xl font-semibold tabular-nums text-zinc-50">
              {impact.potentially_dependent_premises.toLocaleString()}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase text-zinc-500">
              Customer locations plotted
            </dt>
            <dd className="mt-0.5 tabular-nums text-zinc-200">
              {plottedCount.toLocaleString()}
              {impact.returned_customer_points <
              impact.potentially_dependent_premises ? (
                <span className="mt-1 block text-xs text-amber-400/90">
                  API returned {impact.returned_customer_points.toLocaleString()}{" "}
                  of {impact.potentially_dependent_premises.toLocaleString()}{" "}
                  (increase limit up to 5,000).
                </span>
              ) : null}
            </dd>
          </div>
          <div className="rounded-md border border-zinc-800 bg-zinc-900/50 p-3">
            <p className="text-[11px] leading-relaxed text-zinc-500">
              {impact.note}
            </p>
          </div>
          {onSimulateUnavailable && !scenarioActive ? (
            <button
              type="button"
              disabled={simulateLoading}
              onClick={() => onSimulateUnavailable(impact.device.device_key)}
              className="mt-2 w-full rounded-md border border-fuchsia-700/60 bg-fuchsia-950/40 px-3 py-2 text-sm font-medium text-fuchsia-200 hover:bg-fuchsia-900/40 disabled:opacity-50"
            >
              {simulateLoading &&
              activeScenarioDeviceKey === impact.device.device_key
                ? "Running scenario…"
                : "Simulate device unavailable"}
            </button>
          ) : null}
          {scenarioActive ? (
            <p className="mt-2 text-[11px] text-fuchsia-300/80">
              A simulated exposure scenario is active. Use Clear scenario above
              to return to this baseline dependency view.
            </p>
          ) : null}
        </dl>
      ) : null}

      {selectedPremiseId ? (
        <div className="mt-6 border-t border-zinc-800 pt-4">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Premise upstream (map click)
            </h3>
            <button
              type="button"
              onClick={onClearPremise}
              className="text-[11px] text-zinc-500 hover:text-zinc-300"
            >
              Clear
            </button>
          </div>
          <p className="mt-1 font-mono text-xs text-zinc-400">
            {selectedPremiseId}
          </p>
          {upstreamLoading ? (
            <p className="mt-2 text-sm text-zinc-500">Loading upstream…</p>
          ) : null}
          {upstreamError ? (
            <p className="mt-2 text-sm text-red-400">{upstreamError}</p>
          ) : null}
          {upstream ? (
            <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto text-xs">
              {upstream.upstream.length === 0 ? (
                <li className="text-zinc-500">No upstream devices indexed.</li>
              ) : (
                upstream.upstream.map((d) => (
                  <li
                    key={d.device_key}
                    className="rounded border border-zinc-800 px-2 py-1.5"
                  >
                    <span className="text-zinc-200">{d.device_type}</span>
                    <span className="mt-0.5 block font-mono text-[10px] text-zinc-500">
                      {d.device_key}
                    </span>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="mt-6 border-t border-zinc-800 pt-4 text-[11px] text-zinc-600">
          Click an individual customer point on the map to inspect upstream
          equipment via{" "}
          <code className="text-zinc-500">/premises/&#123;id&#125;/upstream</code>
          .
        </p>
      )}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { RestorationNetworkDiagram } from "@/components/restoration/RestorationNetworkDiagram";
import {
  ApiError,
  getRestorationNetwork,
  postRestorationOutagePreview,
  postRestorationSimulate,
} from "@/lib/api";
import { formatCustomerRestorationEta } from "@/lib/restorationEtaCategories";
import { isEquipmentId } from "@/lib/restorationEquipmentLayout";
import {
  buildPlaybackKeyframes,
  frameAtTime,
  playbackDurationHours,
  type PlaybackFrame,
  type TimelineEvent,
} from "@/lib/restorationPlayback";
import {
  computeSimRunId,
  evaluateRestorationCommitted,
  evaluateRestorationPlayback,
} from "@/lib/alertSessionClient";
import { getDemoAlertSessionId } from "@/lib/demoAlertSession";
import type {
  AccessConditions,
  DamageSeverity,
  RestorationSimResponse,
  ScheduleBlock,
} from "@/lib/restorationTypes";

const MODELED_HOME_GROUP = "RES1";
/** Simulated hours advanced per real second during playback (lower = slower animation). */
const PLAYBACK_SPEED_HOURS_PER_SEC = 1;

function scheduleForMode(
  result: RestorationSimResponse,
  compareMode: "step" | "repair" | "both",
): ScheduleBlock | null {
  if (compareMode === "repair") return result.repair_only_optimized;
  return result.step_restoration_optimized ?? result.repair_only_optimized;
}

function homeEtaFromResult(
  result: RestorationSimResponse,
  schedule: ScheduleBlock | null,
) {
  if (!schedule) return null;
  const initialOut = result.initial_snapshot.simulated_outage_group_ids;
  return formatCustomerRestorationEta({
    isInitiallyPowered: !initialOut.includes(MODELED_HOME_GROUP),
    restorationHours: schedule.group_restoration_times[MODELED_HOME_GROUP],
  });
}

function damageSignature(ids: string[]): string {
  return [...ids].sort().join(",");
}

export function RestorationSimulatorPage() {
  const [damaged, setDamaged] = useState<string[]>(["B"]);
  const [previewOutage, setPreviewOutage] = useState<Set<string>>(new Set(["HOSPITAL"]));
  const [totalWorkers, setTotalWorkers] = useState(12);
  const [workersPerCrew, setWorkersPerCrew] = useState(4);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [stormOpen, setStormOpen] = useState(false);
  const [damageSeverity, setDamageSeverity] = useState<DamageSeverity>("minor");
  const [accessConditions, setAccessConditions] = useState<AccessConditions>("normal");
  const [extraMobilizationHours, setExtraMobilizationHours] = useState(0);
  const [compareMode, setCompareMode] = useState<"step" | "repair" | "both">("step");
  const [result, setResult] = useState<RestorationSimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [limitations, setLimitations] = useState<string[]>([]);
  const [laborWarning, setLaborWarning] = useState<string | null>(null);
  const [selectedEquip, setSelectedEquip] = useState<string | null>(null);
  const [playbackTime, setPlaybackTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const playRef = useRef<number | null>(null);
  const [committedSimRunId, setCommittedSimRunId] = useState<string | null>(null);

  const scenarioStale = useMemo(() => {
    if (!result) return false;
    if (damageSignature(damaged) !== damageSignature(result.damaged_component_ids)) {
      return true;
    }
    const sc = result.storm_context;
    if (!sc) return false;
    return (
      sc.damage_severity !== damageSeverity ||
      sc.access_conditions !== accessConditions ||
      sc.extra_mobilization_hours !== extraMobilizationHours
    );
  }, [result, damaged, damageSeverity, accessConditions, extraMobilizationHours]);

  useEffect(() => {
    getRestorationNetwork()
      .then((data) => {
        if (data.labor_references.synthetic_labor_warning) {
          setLaborWarning(
            "Labor durations use a test fixture until the AEP workbook is wired in.",
          );
        }
      })
      .catch(() => setError("Could not load restoration network."));
  }, []);

  useEffect(() => {
    let cancelled = false;
    postRestorationOutagePreview({ damaged_component_ids: damaged })
      .then((data) => {
        if (!cancelled) {
          setPreviewOutage(new Set(data.snapshot.simulated_outage_group_ids));
        }
      })
      .catch(() => {
        if (!cancelled) setPreviewOutage(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [damaged]);

  const activeSchedule: ScheduleBlock | null = useMemo(() => {
    if (!result) return null;
    return scheduleForMode(result, compareMode);
  }, [result, compareMode]);

  const playbackMax = useMemo(() => {
    if (!activeSchedule) return 0;
    return playbackDurationHours(
      activeSchedule.timeline as TimelineEvent[],
      activeSchedule.all_groups_restored_at,
    );
  }, [activeSchedule]);

  const playbackFrames = useMemo(() => {
    if (!result || !activeSchedule) return [];
    return buildPlaybackKeyframes(
      result.initial_snapshot,
      result.damaged_component_ids,
      activeSchedule.timeline as TimelineEvent[],
      playbackMax,
    );
  }, [result, activeSchedule, playbackMax]);

  const displayFrame: PlaybackFrame = useMemo(() => {
    if (result && activeSchedule && playbackFrames.length > 0 && !scenarioStale) {
      return frameAtTime(playbackFrames, playbackTime);
    }
    return {
      timeHours: 0,
      outageGroupIds: previewOutage,
      repairedComponentIds: new Set(),
      inProgress: null,
      statusLine: damaged.length
        ? "Click Simulate Restoration to schedule crews"
        : "Click equipment on the diagram to simulate damage",
    };
  }, [
    result,
    activeSchedule,
    playbackFrames,
    playbackTime,
    previewOutage,
    damaged.length,
    scenarioStale,
  ]);

  useEffect(() => {
    if (!isPlaying || playbackMax <= 0) return;
    const started = performance.now();
    const startT = playbackTime;
    const tick = (now: number) => {
      const elapsedSec = (now - started) / 1000;
      const t = Math.min(playbackMax, startT + elapsedSec * PLAYBACK_SPEED_HOURS_PER_SEC);
      setPlaybackTime(t);
      if (t >= playbackMax) {
        setIsPlaying(false);
        return;
      }
      playRef.current = requestAnimationFrame(tick);
    };
    playRef.current = requestAnimationFrame(tick);
    return () => {
      if (playRef.current != null) cancelAnimationFrame(playRef.current);
    };
  }, [isPlaying, playbackMax]);

  useEffect(() => {
    if (
      !result ||
      !activeSchedule ||
      scenarioStale ||
      !committedSimRunId ||
      playbackTime <= 0
    ) {
      return;
    }
    void evaluateRestorationPlayback(getDemoAlertSessionId(), {
      sim_run_id: committedSimRunId,
      playback_time_hours: playbackTime,
      modeled_group_id: MODELED_HOME_GROUP,
      timeline: activeSchedule.timeline as Record<string, unknown>[],
    }).catch(() => undefined);
  }, [
    playbackTime,
    committedSimRunId,
    result,
    activeSchedule,
    scenarioStale,
  ]);

  const toggleDamage = (id: string) => {
    if (!isEquipmentId(id)) return;
    setIsPlaying(false);
    setPlaybackTime(0);
    setError(null);
    setDamaged((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const run = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    setIsPlaying(false);
    setPlaybackTime(0);
    try {
      const data = await postRestorationSimulate({
        damaged_component_ids: damaged,
        total_workers: totalWorkers,
        workers_per_crew: workersPerCrew,
        enable_step_restoration: compareMode !== "repair",
        damage_severity: damageSeverity,
        access_conditions: accessConditions,
        extra_mobilization_hours: extraMobilizationHours,
      });
      setResult(data);
      setLimitations(data.limitations ?? []);
      const schedule = scheduleForMode(data, compareMode);
      if (schedule) {
        const { sim_run_id } = await computeSimRunId({
          damaged_component_ids: damaged,
          total_workers: totalWorkers,
          workers_per_crew: workersPerCrew,
          enable_step_restoration: compareMode !== "repair",
          damage_severity: damageSeverity,
          access_conditions: accessConditions,
          extra_mobilization_hours: extraMobilizationHours,
          compare_mode: compareMode,
        });
        setCommittedSimRunId(sim_run_id);
        await evaluateRestorationCommitted(getDemoAlertSessionId(), {
          sim_run_id,
          initial_snapshot: data.initial_snapshot as Record<string, unknown>,
          group_restoration_times: schedule.group_restoration_times,
          modeled_group_id: MODELED_HOME_GROUP,
        });
      }
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Simulation failed. Adjust damage or workers and try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [
    damaged,
    totalWorkers,
    workersPerCrew,
    compareMode,
    loading,
    damageSeverity,
    accessConditions,
    extraMobilizationHours,
  ]);

  const stormExplanations = useMemo(() => {
    if (scenarioStale || !result?.storm_context?.eta_explanations?.length) return [];
    return result.storm_context.eta_explanations;
  }, [result, scenarioStale]);

  const modeledEta = useMemo(
    () => (result ? homeEtaFromResult(result, activeSchedule) : null),
    [result, activeSchedule],
  );

  const etaPrimaryText =
    modeledEta?.primaryText ??
    (result && !activeSchedule ? "Restoration time unavailable for this scenario" : null);

  const repairEta =
    result?.repair_only_optimized &&
    formatCustomerRestorationEta({
      isInitiallyPowered: !result.initial_snapshot.simulated_outage_group_ids.includes(
        MODELED_HOME_GROUP,
      ),
      restorationHours:
        result.repair_only_optimized.group_restoration_times[MODELED_HOME_GROUP],
    });

  const stepEta =
    result?.step_restoration_optimized &&
    formatCustomerRestorationEta({
      isInitiallyPowered: !result.initial_snapshot.simulated_outage_group_ids.includes(
        MODELED_HOME_GROUP,
      ),
      restorationHours:
        result.step_restoration_optimized.group_restoration_times[MODELED_HOME_GROUP],
    });

  const showPlayback = Boolean(result && activeSchedule && !scenarioStale);

  return (
    <div className="flex min-h-full flex-col bg-zinc-900 text-zinc-100">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-[1180px] flex-1 flex-col px-4 py-4 xl:max-h-[calc(100vh-3.25rem)] xl:overflow-hidden">
        <header className="shrink-0">
          <h1 className="text-xl font-semibold text-zinc-50">Restoration Simulator</h1>
          <p className="mt-0.5 text-sm text-zinc-400">
            Click equipment to simulate an outage and see how crews restore power.
          </p>
        </header>

        {laborWarning ? (
          <p className="mt-1 shrink-0 text-xs text-amber-200/90">{laborWarning}</p>
        ) : null}

        <div className="mt-3 grid min-h-0 flex-1 gap-4 xl:grid-cols-[minmax(0,1fr)_280px] xl:gap-5">
          <div className="flex min-h-0 flex-col gap-2">
            <RestorationNetworkDiagram
              damaged={damaged}
              frame={displayFrame}
              selectedId={selectedEquip}
              onSelect={setSelectedEquip}
              onToggleDamage={toggleDamage}
            />
            {showPlayback ? (
              <PlaybackBar
                time={playbackTime}
                max={playbackMax}
                isPlaying={isPlaying}
                statusLine={displayFrame.statusLine}
                onPlayPause={() => setIsPlaying((p) => !p)}
                onRestart={() => {
                  setIsPlaying(false);
                  setPlaybackTime(0);
                }}
                onScrub={(t) => {
                  setIsPlaying(false);
                  setPlaybackTime(t);
                }}
              />
            ) : (
              <p className="truncate text-center text-sm text-zinc-500">
                {displayFrame.statusLine}
              </p>
            )}
          </div>

          <aside className="flex shrink-0 flex-col gap-3">
            <label className="block text-sm">
              <span className="text-zinc-400">Available workers</span>
              <input
                type="range"
                min={4}
                max={32}
                step={1}
                value={totalWorkers}
                onChange={(e) => setTotalWorkers(Number(e.target.value))}
                className="mt-2 w-full accent-amber-500"
                disabled={loading}
              />
              <span className="mt-1 block text-center text-xl font-semibold tabular-nums">
                {totalWorkers}
              </span>
            </label>

            <button
              type="button"
              onClick={() => void run()}
              disabled={loading}
              aria-busy={loading}
              className="w-full rounded-lg bg-amber-600 py-3 text-sm font-semibold text-zinc-950 hover:bg-amber-500 disabled:cursor-wait disabled:opacity-70"
            >
              {loading ? "Simulating…" : "Simulate Restoration"}
            </button>

            {error ? (
              <p className="rounded-md border border-red-900/50 bg-red-950/30 px-3 py-2 text-sm text-red-200">
                {error}
              </p>
            ) : null}

            <div
              className={`rounded-xl border p-5 text-center transition-opacity ${
                loading || scenarioStale ? "border-amber-700/30 opacity-90" : "border-amber-700/45"
              } bg-gradient-to-b from-amber-950/25 to-zinc-950/50`}
              aria-live="polite"
            >
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">
                Estimated Restoration Time for Your Home
              </p>
              <p
                className={`mt-3 font-bold leading-tight text-zinc-50 ${
                  etaPrimaryText ? "text-3xl xl:text-4xl" : "text-2xl text-zinc-500"
                } ${loading ? "opacity-80" : ""}`}
              >
                {etaPrimaryText ?? (loading ? "…" : "—")}
              </p>
              {loading && etaPrimaryText ? (
                <p className="mt-1 text-xs text-zinc-400">Updating estimate…</p>
              ) : null}
              {scenarioStale && !loading && etaPrimaryText ? (
                <p className="mt-2 text-xs text-amber-200/80">
                  Scenario changed — simulate again to refresh this estimate.
                </p>
              ) : null}
              {!scenarioStale &&
                stormExplanations.map((line) => (
                  <p key={line} className="mt-2 text-xs leading-snug text-zinc-400">
                    {line}
                  </p>
                ))}
            </div>

            <StormConditionsPanel
              open={stormOpen}
              onToggle={() => setStormOpen((o) => !o)}
              damageSeverity={damageSeverity}
              onDamageSeverity={setDamageSeverity}
              accessConditions={accessConditions}
              onAccessConditions={setAccessConditions}
              extraMobilizationHours={extraMobilizationHours}
              onExtraMobilizationHours={setExtraMobilizationHours}
            />

            <AdvancedPanel
              open={advancedOpen}
              onToggle={() => setAdvancedOpen((o) => !o)}
              workersPerCrew={workersPerCrew}
              onWorkersPerCrew={setWorkersPerCrew}
              compareMode={compareMode}
              onCompareMode={setCompareMode}
              repairEta={repairEta?.primaryText}
              stepEta={stepEta?.primaryText}
              showComparison={Boolean(result && compareMode === "both")}
            />
          </aside>
        </div>

        <footer className="mt-2 shrink-0 pb-1 text-[11px] text-zinc-500">
          <p>
            Illustrative network. Restoration times are simulated estimates, not live AEP
            updates.{" "}
            <HowItWorksInline limitations={limitations} result={result} />
          </p>
        </footer>
      </main>
    </div>
  );
}

function HowItWorksInline({
  limitations,
  result,
}: {
  limitations: string[];
  result: RestorationSimResponse | null;
}) {
  return (
    <details className="inline">
      <summary className="cursor-pointer text-zinc-400 underline-offset-2 hover:underline">
        How it works
      </summary>
      <span className="mt-1 block max-w-3xl text-zinc-500">
        Schedules use AEP labor references (direct person-hours × quantity × 4.5 ILM ÷ crew
        size), repair precedence, and optional tie switching. Storm settings adjust quantity
        and access start times per config/restoration/storm_operational_assumptions.json.
        {result?.comparison.hospital_restore_delta_hours != null &&
        result.comparison.hospital_restore_delta_hours > 0
          ? " Step restoration may restore the hospital sooner than repair-only here."
          : null}{" "}
        {limitations.length > 0 ? limitations.join(" ") : null}
      </span>
    </details>
  );
}

function StormConditionsPanel({
  open,
  onToggle,
  damageSeverity,
  onDamageSeverity,
  accessConditions,
  onAccessConditions,
  extraMobilizationHours,
  onExtraMobilizationHours,
}: {
  open: boolean;
  onToggle: () => void;
  damageSeverity: DamageSeverity;
  onDamageSeverity: (v: DamageSeverity) => void;
  accessConditions: AccessConditions;
  onAccessConditions: (v: AccessConditions) => void;
  extraMobilizationHours: number;
  onExtraMobilizationHours: (n: number) => void;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/40">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-zinc-300"
        aria-expanded={open}
      >
        Storm conditions
        <span className="text-zinc-500">{open ? "▾" : "▸"}</span>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-zinc-800 px-3 py-3 text-sm">
          <label className="block">
            <span className="text-zinc-400">Damage severity</span>
            <select
              value={damageSeverity}
              onChange={(e) => onDamageSeverity(e.target.value as DamageSeverity)}
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5"
            >
              <option value="minor">Minor — baseline unit scope</option>
              <option value="moderate">Moderate — expanded quantities</option>
              <option value="major">Major — heavy storm scope</option>
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-400">Access conditions</span>
            <select
              value={accessConditions}
              onChange={(e) => onAccessConditions(e.target.value as AccessConditions)}
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5"
            >
              <option value="normal">Normal</option>
              <option value="difficult">Difficult</option>
              <option value="restricted">Restricted</option>
            </select>
          </label>
          <label className="block">
            <span className="text-zinc-400">Extra crew mobilization (hours)</span>
            <input
              type="number"
              min={0}
              max={168}
              step={1}
              value={extraMobilizationHours}
              onChange={(e) => onExtraMobilizationHours(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5"
            />
          </label>
          <p className="text-[11px] leading-snug text-zinc-500">
            Simulated operational overlays only. Severity changes work quantity on damaged
            components; access controls when repairs may start — not an extra multiplier on
            AEP labor hours.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function AdvancedPanel({
  open,
  onToggle,
  workersPerCrew,
  onWorkersPerCrew,
  compareMode,
  onCompareMode,
  repairEta,
  stepEta,
  showComparison,
}: {
  open: boolean;
  onToggle: () => void;
  workersPerCrew: number;
  onWorkersPerCrew: (n: number) => void;
  compareMode: "step" | "repair" | "both";
  onCompareMode: (m: "step" | "repair" | "both") => void;
  repairEta?: string;
  stepEta?: string;
  showComparison: boolean;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/40">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-zinc-300"
        aria-expanded={open}
      >
        Advanced settings
        <span className="text-zinc-500">{open ? "▾" : "▸"}</span>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-zinc-800 px-3 py-3 text-sm">
          <label className="block">
            <span className="text-zinc-400">Workers per crew</span>
            <select
              value={workersPerCrew}
              onChange={(e) => onWorkersPerCrew(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5"
            >
              {[2, 3, 4, 5, 6, 7, 8].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend className="text-zinc-400">Calculation mode</legend>
            <div className="mt-1 space-y-1">
              {(
                [
                  ["step", "Optimized step restoration (default)"],
                  ["repair", "Repair-only"],
                  ["both", "Compare both"],
                ] as const
              ).map(([value, label]) => (
                <label key={value} className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="compareMode"
                    checked={compareMode === value}
                    onChange={() => onCompareMode(value)}
                  />
                  <span className="text-zinc-300">{label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {showComparison ? (
            <ul className="space-y-1 text-xs text-zinc-400">
              <li>Step restoration: {stepEta ?? "—"}</li>
              <li>Repair-only: {repairEta ?? "—"}</li>
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function PlaybackBar({
  time,
  max,
  isPlaying,
  statusLine,
  onPlayPause,
  onRestart,
  onScrub,
}: {
  time: number;
  max: number;
  isPlaying: boolean;
  statusLine: string;
  onPlayPause: () => void;
  onRestart: () => void;
  onScrub: (t: number) => void;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 px-3 py-2">
      <p className="truncate text-sm text-zinc-300">{statusLine}</p>
      <div className="mt-2 flex items-center gap-2">
        <button
          type="button"
          onClick={onPlayPause}
          className="rounded-md border border-zinc-700 px-3 py-1 text-xs hover:bg-zinc-800"
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          onClick={onRestart}
          className="rounded-md border border-zinc-700 px-3 py-1 text-xs hover:bg-zinc-800"
        >
          Restart
        </button>
        <input
          type="range"
          min={0}
          max={max || 1}
          step={0.05}
          value={time}
          onChange={(e) => onScrub(Number(e.target.value))}
          className="min-w-0 flex-1 accent-emerald-500"
          aria-label="Restoration timeline"
        />
      </div>
    </div>
  );
}

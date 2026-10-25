import { equipmentDisplayName } from "./restorationEquipmentLayout";

export interface RestorationSnapshot {
  simulated_outage_group_ids: string[];
  powered_group_ids?: string[];
}

export interface TimelineEvent {
  time_hours?: number;
  start_hours?: number;
  finish_hours?: number;
  event?: string;
  component_id?: string;
  action_id?: string;
  group_id?: string;
  reason?: string;
  snapshot?: RestorationSnapshot & { groups?: Record<string, boolean> };
}

export interface PlaybackFrame {
  timeHours: number;
  outageGroupIds: Set<string>;
  repairedComponentIds: Set<string>;
  inProgress: {
    kind: "repair" | "switch";
    componentId?: string;
    actionId?: string;
  } | null;
  statusLine: string;
}

const SWITCH_STATUS: Record<string, string> = {
  OPEN_S1: "Crew opening hospital sectionalizer",
  CLOSE_S2: "Crew closing tie switch to backfeed hospital",
  CLOSE_S1: "Crew reclosing hospital sectionalizer",
};

function snapshotAtTime(
  initial: RestorationSnapshot,
  timeline: TimelineEvent[],
  t: number,
): Set<string> {
  let outage = new Set(initial.simulated_outage_group_ids);
  for (const ev of timeline) {
    const finish = ev.finish_hours ?? ev.time_hours;
    if (finish == null || finish > t) continue;
    if (ev.snapshot?.simulated_outage_group_ids) {
      outage = new Set(ev.snapshot.simulated_outage_group_ids);
    } else if (ev.event === "group_restored" && ev.group_id) {
      outage.delete(ev.group_id);
    }
  }
  return outage;
}

function inProgressAt(timeline: TimelineEvent[], t: number): PlaybackFrame["inProgress"] {
  for (const ev of timeline) {
    const start = ev.start_hours;
    const finish = ev.finish_hours ?? ev.time_hours;
    if (start == null || finish == null) continue;
    if (start <= t && t < finish) {
      if (ev.event === "repair_complete" || ev.component_id) {
        return { kind: "repair", componentId: ev.component_id };
      }
      if (ev.event === "switching_complete" || ev.action_id) {
        return { kind: "switch", actionId: ev.action_id };
      }
    }
  }
  return null;
}

function repairedAt(timeline: TimelineEvent[], t: number): Set<string> {
  const done = new Set<string>();
  for (const ev of timeline) {
    if (ev.event !== "repair_complete" || !ev.component_id) continue;
    const finish = ev.finish_hours ?? ev.time_hours;
    if (finish != null && finish <= t) done.add(ev.component_id);
  }
  return done;
}

export function playbackStatusLine(
  inProgress: PlaybackFrame["inProgress"],
  outageGroupIds: Set<string>,
): string {
  if (inProgress?.kind === "repair" && inProgress.componentId) {
    return `Crew repairing ${equipmentDisplayName(inProgress.componentId).toLowerCase()}`;
  }
  if (inProgress?.kind === "switch" && inProgress.actionId) {
    return SWITCH_STATUS[inProgress.actionId] ?? "Crew performing switching";
  }
  if (outageGroupIds.has("RES1")) {
    return "Homes still without power";
  }
  if (outageGroupIds.size === 0) {
    return "All served areas restored";
  }
  return "Restoration in progress";
}

export function buildPlaybackKeyframes(
  initialSnapshot: RestorationSnapshot,
  damagedComponentIds: string[],
  timeline: TimelineEvent[],
  maxTimeHours: number,
): PlaybackFrame[] {
  const keyTimes = new Set<number>([0]);
  for (const ev of timeline) {
    if (ev.start_hours != null) keyTimes.add(ev.start_hours);
    if (ev.finish_hours != null) keyTimes.add(ev.finish_hours);
    if (ev.time_hours != null) keyTimes.add(ev.time_hours);
  }
  if (maxTimeHours > 0) keyTimes.add(maxTimeHours);
  const times = Array.from(keyTimes).sort((a, b) => a - b);

  return times.map((timeHours) => {
    const outageGroupIds = snapshotAtTime(initialSnapshot, timeline, timeHours);
    const repairedComponentIds = repairedAt(timeline, timeHours);
    const inProgress = inProgressAt(timeline, timeHours);
    return {
      timeHours,
      outageGroupIds,
      repairedComponentIds,
      inProgress,
      statusLine: playbackStatusLine(inProgress, outageGroupIds),
    };
  });
}

export function frameAtTime(frames: PlaybackFrame[], timeHours: number): PlaybackFrame {
  if (frames.length === 0) {
    return {
      timeHours: 0,
      outageGroupIds: new Set(),
      repairedComponentIds: new Set(),
      inProgress: null,
      statusLine: "Run a simulation to preview restoration",
    };
  }
  let pick = frames[0];
  for (const f of frames) {
    if (f.timeHours <= timeHours) pick = f;
    else break;
  }
  return pick;
}

export function playbackDurationHours(
  timeline: TimelineEvent[],
  fallback: number | null | undefined,
): number {
  let max = fallback ?? 0;
  for (const ev of timeline) {
    const finish = ev.finish_hours ?? ev.time_hours;
    if (finish != null && finish > max) max = finish;
  }
  return max;
}

/** Ensures restored groups never appear powered before snapshot allows (sanity check for tests). */
export function groupPoweredOnlyWhenConnected(
  frames: PlaybackFrame[],
  groupId: string,
  initialOutage: boolean,
): boolean {
  if (!initialOutage) {
    return frames.every((f) => !f.outageGroupIds.has(groupId));
  }
  let seenOut = true;
  for (const f of frames) {
    const out = f.outageGroupIds.has(groupId);
    if (seenOut && !out) seenOut = false;
    if (!seenOut && out) return false;
  }
  return true;
}

export function damagedSetFromUserSelection(damagedComponentIds: string[]): Set<string> {
  return new Set(damagedComponentIds);
}

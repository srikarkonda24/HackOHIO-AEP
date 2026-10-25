import { describe, expect, it } from "vitest";
import {
  buildPlaybackKeyframes,
  frameAtTime,
  groupPoweredOnlyWhenConnected,
  playbackDurationHours,
} from "./restorationPlayback";

describe("buildPlaybackKeyframes", () => {
  it("marks in-progress repair between start and finish", () => {
    const frames = buildPlaybackKeyframes(
      { simulated_outage_group_ids: ["RES1"] },
      ["B"],
      [
        {
          event: "repair_complete",
          component_id: "B",
          start_hours: 0,
          finish_hours: 2,
        },
      ],
      2,
    );
    const mid = frames.find((f) => f.timeHours === 0);
    expect(mid?.inProgress?.componentId).toBe("B");
    const done = frames.find((f) => f.timeHours === 2);
    expect(done?.repairedComponentIds.has("B")).toBe(true);
    expect(done?.inProgress).toBeNull();
  });

  it("updates outage from switching snapshot", () => {
    const frames = buildPlaybackKeyframes(
      { simulated_outage_group_ids: ["HOSPITAL", "RES1"] },
      ["B"],
      [
        {
          event: "switching_complete",
          action_id: "CLOSE_S2",
          start_hours: 1,
          finish_hours: 3,
          snapshot: { simulated_outage_group_ids: ["RES1"] },
        },
      ],
      3,
    );
    const after = frameAtTime(frames, 3);
    expect(after.outageGroupIds.has("HOSPITAL")).toBe(false);
    expect(after.outageGroupIds.has("RES1")).toBe(true);
  });
});

describe("playbackDurationHours", () => {
  it("uses latest finish in timeline", () => {
    expect(
      playbackDurationHours(
        [{ finish_hours: 2.5 }, { finish_hours: 4.1 }],
        null,
      ),
    ).toBe(4.1);
  });
});

describe("groupPoweredOnlyWhenConnected", () => {
  it("does not flip a group back to outage after restore", () => {
    const frames = buildPlaybackKeyframes(
      { simulated_outage_group_ids: ["RES1"] },
      ["C"],
      [
        {
          event: "group_restored",
          group_id: "RES1",
          time_hours: 5,
          finish_hours: 5,
          snapshot: { simulated_outage_group_ids: [] },
        },
      ],
      5,
    );
    expect(groupPoweredOnlyWhenConnected(frames, "RES1", true)).toBe(true);
  });
});

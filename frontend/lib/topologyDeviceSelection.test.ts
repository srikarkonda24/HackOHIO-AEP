import { describe, expect, it } from "vitest";
import {
  clearGisSelectionState,
  equipmentSearchSelectUpdates,
} from "./topologyDeviceSelection";
import { DEMO_DEVICE_KEY } from "./constants";

describe("equipmentSearchSelectUpdates", () => {
  it("clears GIS and scenario when selecting a new device from search", () => {
    const updates = equipmentSearchSelectUpdates(
      DEMO_DEVICE_KEY,
      "eo_isolating_eqpt_inst*999",
    );
    expect(updates.selectedDeviceKey).toBe(DEMO_DEVICE_KEY);
    expect(updates.clearGisSelection).toBe(true);
    expect(updates.clearScenario).toBe(true);
    expect(updates.refreshImpact).toBe(false);
  });

  it("forces impact refresh when re-selecting the same device while GIS may differ", () => {
    const updates = equipmentSearchSelectUpdates(
      DEMO_DEVICE_KEY,
      DEMO_DEVICE_KEY,
    );
    expect(updates.refreshImpact).toBe(true);
    expect(updates.clearGisSelection).toBe(true);
  });
});

describe("clearGisSelectionState", () => {
  it("returns empty GIS inspect state", () => {
    expect(clearGisSelectionState()).toEqual({
      selectedAsset: null,
      locationMatch: null,
      matchError: null,
      matchLoading: false,
    });
  });
});

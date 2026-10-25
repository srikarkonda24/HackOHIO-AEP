import { describe, expect, it } from "vitest";
import {
  EQUIPMENT_IDS,
  EQUIPMENT_LAYOUT,
  isEquipmentId,
} from "./restorationEquipmentLayout";

describe("restoration equipment layout", () => {
  it("maps all seven backend components A–G", () => {
    expect(EQUIPMENT_LAYOUT.map((e) => e.id).sort()).toEqual([...EQUIPMENT_IDS].sort());
  });

  it("recognizes equipment ids for diagram clicks", () => {
    for (const id of EQUIPMENT_IDS) {
      expect(isEquipmentId(id)).toBe(true);
    }
    expect(isEquipmentId("S1")).toBe(false);
  });
});

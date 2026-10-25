import { describe, expect, it } from "vitest";
import {
  CARD_H,
  CARD_W,
  DIAGRAM_EQUIPMENT,
  DIAGRAM_FACILITIES,
  minEquipmentCenterDistance,
} from "./restorationDiagramLayout";
import { EQUIPMENT_IDS } from "./restorationEquipmentLayout";

describe("restorationDiagramLayout", () => {
  it("places all seven graph components", () => {
    expect(DIAGRAM_EQUIPMENT.map((e) => e.id).sort()).toEqual([...EQUIPMENT_IDS].sort());
  });

  it("shows all five customer groups on the diagram", () => {
    expect(DIAGRAM_FACILITIES.map((f) => f.id).sort()).toEqual(
      ["FIRE", "HOSPITAL", "RES1", "RES2", "RES3"].sort(),
    );
  });

  it("keeps equipment cards spaced apart on desktop layout", () => {
    expect(minEquipmentCenterDistance()).toBeGreaterThan(CARD_W * 0.85);
  });

  it("uses readable card dimensions", () => {
    expect(CARD_W).toBeGreaterThanOrEqual(110);
    expect(CARD_H).toBeGreaterThanOrEqual(40);
  });
});

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  equipmentVisualState,
  RestorationNetworkDiagram,
} from "./RestorationNetworkDiagram";
import { EQUIPMENT_LAYOUT } from "@/lib/restorationEquipmentLayout";

describe("RestorationNetworkDiagram", () => {
  const frame = {
    timeHours: 0,
    outageGroupIds: new Set(["HOSPITAL"]),
    repairedComponentIds: new Set<string>(),
    inProgress: null,
    statusLine: "test",
  };

  it("renders clickable equipment for all graph components", () => {
    render(
      <RestorationNetworkDiagram
        damaged={["B"]}
        frame={frame}
        selectedId={null}
        onSelect={() => {}}
        onToggleDamage={() => {}}
      />,
    );
    for (const eq of EQUIPMENT_LAYOUT) {
      const damaged = eq.id === "B";
      expect(
        screen.getByRole("button", {
          name: `${eq.displayName}, ${damaged ? "damaged" : "intact"}. Toggle simulated damage.`,
        }),
      ).toBeTruthy();
    }
  });

  it("shows all customer groups", () => {
    render(
      <RestorationNetworkDiagram
        damaged={[]}
        frame={{ ...frame, outageGroupIds: new Set() }}
        selectedId={null}
        onSelect={() => {}}
        onToggleDamage={() => {}}
      />,
    );
    expect(screen.getAllByText("Your home").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Hospital").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Fire station").length).toBeGreaterThan(0);
  });
});

describe("equipmentVisualState colors", () => {
  const base = {
    timeHours: 0,
    outageGroupIds: new Set<string>(),
    repairedComponentIds: new Set<string>(),
    inProgress: null,
    statusLine: "",
  };

  it("uses neutral for intact equipment", () => {
    expect(equipmentVisualState("A", false, base)).toBe("intact");
  });

  it("uses in-progress only on the active repair target", () => {
    expect(
      equipmentVisualState("B", true, {
        ...base,
        inProgress: { kind: "repair", componentId: "B" },
      }),
    ).toBe("in_progress");
  });

  it("does not mark intact equipment as in progress", () => {
    expect(
      equipmentVisualState("A", false, {
        ...base,
        inProgress: { kind: "repair", componentId: "B" },
      }),
    ).toBe("intact");
  });
});

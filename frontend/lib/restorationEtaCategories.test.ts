import { describe, expect, it } from "vitest";
import {
  formatCustomerRestorationEta,
  restorationEtaCategoryRange,
  restorationHoursToCategory,
  restorationUncertaintyBandHours,
} from "./restorationEtaCategories";

describe("restorationHoursToCategory boundaries", () => {
  it("maps short repairs to Within 1 day", () => {
    expect(restorationHoursToCategory(3)).toBe("Within 1 day");
    expect(restorationHoursToCategory(0)).toBe("Within 1 day");
  });

  it("maps boundary hours inclusively to the lower bucket", () => {
    expect(restorationHoursToCategory(24)).toBe("Within 1 day");
    expect(restorationHoursToCategory(48)).toBe("1–2 days");
    expect(restorationHoursToCategory(72)).toBe("2–3 days");
    expect(restorationHoursToCategory(96)).toBe("3–4 days");
    expect(restorationHoursToCategory(120)).toBe("4–5 days");
    expect(restorationHoursToCategory(168)).toBe("5–7 days (within 1 week)");
  });

  it("maps just above boundaries to the next bucket", () => {
    expect(restorationHoursToCategory(24.0001)).toBe("1–2 days");
    expect(restorationHoursToCategory(48.0001)).toBe("2–3 days");
    expect(restorationHoursToCategory(72.0001)).toBe("3–4 days");
    expect(restorationHoursToCategory(96.0001)).toBe("4–5 days");
    expect(restorationHoursToCategory(120.0001)).toBe("5–7 days (within 1 week)");
    expect(restorationHoursToCategory(168.0001)).toBe("More than 1 week");
  });
});

describe("restorationEtaCategoryRange", () => {
  it("does not split a 3-hour estimate across multiple day buckets", () => {
    const { low, high } = restorationUncertaintyBandHours(3);
    expect(restorationEtaCategoryRange(low, high)).toEqual(["Within 1 day"]);
  });

  it("shows a range when uncertainty crosses bucket boundaries", () => {
    const { low, high } = restorationUncertaintyBandHours(22);
    expect(low).toBeLessThan(24);
    expect(high).toBeGreaterThan(24);
    expect(restorationEtaCategoryRange(low, high)).toEqual([
      "Within 1 day",
      "1–2 days",
    ]);
  });
});

describe("formatCustomerRestorationEta", () => {
  it('shows "No simulated outage" when the modeled customer stays powered', () => {
    const out = formatCustomerRestorationEta({
      isInitiallyPowered: true,
      restorationHours: 0,
    });
    expect(out.primaryText).toBe("No simulated outage");
  });

  it("uses API restoration hours without inventing extra day buckets", () => {
    const out = formatCustomerRestorationEta({
      isInitiallyPowered: false,
      restorationHours: 3,
    });
    expect(out.primaryText).toBe("Within 1 day");
  });
});

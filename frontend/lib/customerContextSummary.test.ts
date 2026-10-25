import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import type { CustomerNetworkContext } from "./networkContextTypes";
import {
  hasIncompleteData,
  incompleteDataMessage,
  summarizeNetworkKnowledge,
  summarizeServiceLocation,
} from "./customerContextSummary";

const samplePath = join(
  process.cwd(),
  "..",
  "data",
  "processed",
  "network_context_000052580.json",
);

function loadSample(): CustomerNetworkContext {
  return JSON.parse(readFileSync(samplePath, "utf8")) as CustomerNetworkContext;
}

describe("customerContextSummary", () => {
  it("describes service location in plain language for 000052580", () => {
    const ctx = loadSample();
    const lines = summarizeServiceLocation(ctx);
    expect(lines.some((l) => l.includes("VINTON"))).toBe(true);
    expect(lines.some((l) => l.includes("service transformer"))).toBe(true);
    expect(lines.join(" ")).not.toMatch(/eo_power_xfrmr_inst/);
  });

  it("summarizes upstream knowledge without raw device keys", () => {
    const ctx = loadSample();
    const lines = summarizeNetworkKnowledge(ctx);
    const text = lines.join(" ");
    expect(text).toMatch(/protective device|transformer/i);
    expect(text).not.toMatch(/321305938/);
    expect(text).toMatch(/not a step-by-step map/i);
  });

  it("flags incomplete data when upstream list is empty", () => {
    const ctx = loadSample();
    const empty: CustomerNetworkContext = {
      ...ctx,
      upstream_device_count: 0,
      upstream_devices: [],
    };
    expect(hasIncompleteData(empty)).toBe(true);
    expect(incompleteDataMessage(empty)).toMatch(/No upstream/);
  });

  it("reports missing customer clip row", () => {
    const ctx = loadSample();
    const partial: CustomerNetworkContext = {
      ...ctx,
      missing_or_partial: ["customer_clip_record_not_found_for_premise"],
    };
    expect(incompleteDataMessage(partial)).toMatch(/no matching customer shapefile/);
  });
});

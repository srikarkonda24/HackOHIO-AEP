import { describe, expect, it } from "vitest";
import { getDemoAlertSessionId } from "./demoAlertSession";

describe("demoAlertSession", () => {
  it("returns a stable session id in browser-like env", () => {
    const a = getDemoAlertSessionId();
    const b = getDemoAlertSessionId();
    expect(a).toBe(b);
    expect(a.length).toBeGreaterThan(8);
  });
});

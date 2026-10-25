import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EquipmentSearch } from "./EquipmentSearch";
import * as api from "@/lib/api";
import { DEMO_DEVICE_KEY } from "@/lib/constants";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {},
  searchDevices: vi.fn(),
}));

const mockRow = {
  device_key: DEMO_DEVICE_KEY,
  device_type: "Recloser (Electronic)",
  location_id: "37800281C36078",
  dependent_premises: 2811,
};

describe("EquipmentSearch", () => {
  beforeEach(() => {
    vi.mocked(api.searchDevices).mockResolvedValue({ devices: [mockRow] });
  });

  it("calls onSelectRow when clicking a result", async () => {
    const onSelectRow = vi.fn();
    const user = userEvent.setup();

    render(
      <EquipmentSearch selectedDeviceKey={null} onSelectRow={onSelectRow} />,
    );

    await user.type(screen.getByRole("searchbox"), "321305938");
    const result = await screen.findByRole("button", {
      name: /Recloser \(Electronic\)/i,
    });
    await user.click(result);

    expect(onSelectRow).toHaveBeenCalledTimes(1);
    expect(onSelectRow).toHaveBeenCalledWith(mockRow);
  });
});

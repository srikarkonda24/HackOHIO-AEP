import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useCallback, useState } from "react";
import { EquipmentSearch } from "@/components/search/EquipmentSearch";
import {
  clearGisSelectionState,
  equipmentSearchSelectUpdates,
} from "@/lib/topologyDeviceSelection";
import { DEMO_DEVICE_KEY } from "@/lib/constants";
import type { DeviceSearchRow, SelectedGisAsset } from "@/lib/types";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {},
  searchDevices: vi.fn(),
}));

const mockHydraulicAsset: SelectedGisAsset = {
  layerId: "reclosers",
  featureId: "hydraulic-1",
  locationId: "OTHERLOC",
  geometry: { type: "Point", coordinates: [-82, 40] },
  properties: {
    _layer: "reclosers",
    _feature_id: "hydraulic-1",
    device_typ: "Recloser (Hydraulic)",
    _topology_match: true,
  },
};

const mockSearchRow: DeviceSearchRow = {
  device_key: DEMO_DEVICE_KEY,
  device_type: "Recloser (Electronic)",
  location_id: "37800281C36078",
  dependent_premises: 2811,
};

function SearchWithGisHarness() {
  const [selectedDeviceKey, setSelectedDeviceKey] = useState<string | null>(
    "eo_isolating_eqpt_inst*other",
  );
  const [selectedAsset, setSelectedAsset] = useState<SelectedGisAsset | null>(
    mockHydraulicAsset,
  );

  const handleSearchSelect = useCallback(
    (row: DeviceSearchRow) => {
      equipmentSearchSelectUpdates(row.device_key, selectedDeviceKey);
      const cleared = clearGisSelectionState();
      setSelectedAsset(cleared.selectedAsset);
      setSelectedDeviceKey(row.device_key);
    },
    [selectedDeviceKey],
  );

  return (
    <>
      <EquipmentSearch
        selectedDeviceKey={selectedDeviceKey}
        onSelectRow={handleSearchSelect}
      />
      <p data-testid="device-key">{selectedDeviceKey}</p>
      <p data-testid="gis-asset">
        {selectedAsset ? selectedAsset.properties.device_typ : "none"}
      </p>
    </>
  );
}

describe("search selection with GIS asset selected (regression)", () => {
  beforeEach(() => {
    vi.mocked(api.searchDevices).mockResolvedValue({
      devices: [mockSearchRow],
    });
  });

  it("updates topology device and clears GIS inspect state on result click", async () => {
    const user = userEvent.setup();
    render(<SearchWithGisHarness />);

    expect(screen.getByTestId("gis-asset").textContent).toBe(
      "Recloser (Hydraulic)",
    );

    await user.type(screen.getByRole("searchbox"), "321305938");
    await user.click(
      await screen.findByRole("button", { name: /Recloser \(Electronic\)/i }),
    );

    expect(screen.getByTestId("device-key").textContent).toBe(DEMO_DEVICE_KEY);
    expect(screen.getByTestId("gis-asset").textContent).toBe("none");
  });
});

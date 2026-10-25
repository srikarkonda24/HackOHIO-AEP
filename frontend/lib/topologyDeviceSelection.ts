/** Pure selection updates when picking a topology device from equipment search. */
export function equipmentSearchSelectUpdates(
  deviceKey: string,
  currentDeviceKey: string | null,
): {
  selectedDeviceKey: string;
  refreshImpact: boolean;
  clearGisSelection: true;
  clearScenario: true;
} {
  return {
    selectedDeviceKey: deviceKey,
    refreshImpact: currentDeviceKey === deviceKey,
    clearGisSelection: true,
    clearScenario: true,
  };
}

export function clearGisSelectionState(): {
  selectedAsset: null;
  locationMatch: null;
  matchError: null;
  matchLoading: false;
} {
  return {
    selectedAsset: null,
    locationMatch: null,
    matchError: null,
    matchLoading: false,
  };
}

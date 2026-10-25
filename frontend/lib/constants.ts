/** Verified demo device — Recloser (Electronic), 2,811 potentially dependent premises. */
export const DEMO_DEVICE_KEY = "eo_isolating_eqpt_inst*321305938";

/** API cap per ARCHITECTURE.md / api.py (`min(limit, 5000)`). */
export const IMPACT_CUSTOMER_LIMIT = 5000;

export const API_BASE = "/api/backend";

/** Example premise for customer network context demo (validated in docs). */
export const EXAMPLE_CUSTOMER_PREMISE_ID = "000052580";

/** M3A default map layers (dense layers off until toggled). */
export const DEFAULT_LAYER_VISIBILITY: Record<string, boolean> = {
  primary: true,
  reclosers: true,
  switches: false,
  fuses: false,
  transformers: false,
  damage: false,
  secondary: false,
  poles: false,
  emergency: false,
};

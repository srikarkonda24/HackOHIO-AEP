/** Customer-facing restoration ETA buckets (hours stay internal elsewhere). */

export const RESTORATION_ETA_CATEGORY_LABELS = [
  "Within 1 day",
  "1–2 days",
  "2–3 days",
  "3–4 days",
  "4–5 days",
  "5–7 days (within 1 week)",
  "More than 1 week",
] as const;

export type RestorationEtaCategoryLabel =
  (typeof RESTORATION_ETA_CATEGORY_LABELS)[number];

/** Upper inclusive bound in hours for each bucket (first bucket: 0–24 h). */
const BUCKET_UPPER_INCLUSIVE_HOURS = [24, 48, 72, 96, 120, 168, Infinity] as const;

const NO_OUTAGE_LABEL = "No simulated outage";

/**
 * Map a single restoration duration (hours) to exactly one customer ETA category.
 * Boundaries: 24, 48, 72, 96, 120, 168 hours are inclusive in the lower bucket
 * (e.g. 24 h → Within 1 day; 24.0001 h → 1–2 days).
 */
export function restorationHoursToCategory(
  hours: number,
): RestorationEtaCategoryLabel {
  if (hours <= BUCKET_UPPER_INCLUSIVE_HOURS[0]) {
    return RESTORATION_ETA_CATEGORY_LABELS[0];
  }
  for (let i = 1; i < BUCKET_UPPER_INCLUSIVE_HOURS.length; i++) {
    const upper = BUCKET_UPPER_INCLUSIVE_HOURS[i];
    if (hours <= upper) {
      return RESTORATION_ETA_CATEGORY_LABELS[i];
    }
  }
  return RESTORATION_ETA_CATEGORY_LABELS[RESTORATION_ETA_CATEGORY_LABELS.length - 1];
}

function categoryIndex(hours: number): number {
  const label = restorationHoursToCategory(hours);
  return RESTORATION_ETA_CATEGORY_LABELS.indexOf(label);
}

/** ±10% labor uncertainty band applied to modeled customer restore time. */
export function restorationUncertaintyBandHours(centralHours: number): {
  low: number;
  high: number;
} {
  return {
    low: centralHours * 0.9,
    high: centralHours * 1.1,
  };
}

/**
 * All category labels touched by an uncertainty interval [lowHours, highHours].
 */
export function restorationEtaCategoryRange(
  lowHours: number,
  highHours: number,
): RestorationEtaCategoryLabel[] {
  const lo = Math.min(lowHours, highHours);
  const hi = Math.max(lowHours, highHours);
  const start = categoryIndex(lo);
  const end = categoryIndex(hi);
  return RESTORATION_ETA_CATEGORY_LABELS.slice(start, end + 1);
}

export function formatRestorationEtaCategoryRange(
  labels: RestorationEtaCategoryLabel[],
): string {
  if (labels.length === 0) return "";
  if (labels.length === 1) return labels[0];
  return `${labels[0]} to ${labels[labels.length - 1]}`;
}

export interface CustomerRestorationEtaInput {
  /** Group is not in the initial simulated outage set. */
  isInitiallyPowered: boolean;
  /** Modeled customer group restore time from simulation (hours), if outaged. */
  restorationHours: number | null | undefined;
}

export interface CustomerRestorationEtaDisplay {
  primaryText: string;
  categoryLabels: RestorationEtaCategoryLabel[];
}

/**
 * Customer-facing ETA for the modeled service location.
 */
export function formatCustomerRestorationEta(
  input: CustomerRestorationEtaInput,
): CustomerRestorationEtaDisplay {
  if (input.isInitiallyPowered) {
    return {
      primaryText: NO_OUTAGE_LABEL,
      categoryLabels: [],
    };
  }
  const central = input.restorationHours;
  if (central == null || Number.isNaN(central)) {
    return {
      primaryText: "Restoration time unavailable for this scenario",
      categoryLabels: [],
    };
  }
  const { low, high } = restorationUncertaintyBandHours(central);
  const categoryLabels = restorationEtaCategoryRange(low, high);
  return {
    primaryText: formatRestorationEtaCategoryRange(categoryLabels),
    categoryLabels,
  };
}

export { NO_OUTAGE_LABEL };

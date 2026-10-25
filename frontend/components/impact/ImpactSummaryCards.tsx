"use client";

interface ImpactSummaryCardsProps {
  potentiallyDependent: number | null;
  returnedPoints: number | null;
  plottedPoints: number | null;
  deviceType: string | null;
  loading: boolean;
  scenarioActive?: boolean;
}

function formatCount(n: number | null): string {
  if (n === null) return "—";
  return n.toLocaleString();
}

export function ImpactSummaryCards({
  potentiallyDependent,
  returnedPoints,
  plottedPoints,
  deviceType,
  loading,
  scenarioActive = false,
}: ImpactSummaryCardsProps) {
  const cards: {
    label: string;
    value: string;
    hint: string;
    valueClassName: string;
  }[] = [
    {
      label: scenarioActive
        ? "Modeled potential exposure (premises)"
        : "Potentially Dependent Premises",
      value: formatCount(potentiallyDependent),
      hint: scenarioActive
        ? "Simulated device-unavailable scenario — not a confirmed outage"
        : "Upstream dependency membership — not confirmed outages",
      valueClassName: "text-2xl font-semibold tabular-nums",
    },
    {
      label: scenarioActive
        ? "Customer points (scenario API)"
        : "Points returned by API",
      value: formatCount(returnedPoints),
      hint: scenarioActive
        ? "Full dependency set from /scenarios/device-unavailable (no 5,000 cap)"
        : "Customer rows in /devices/impact response (limit capped at 5,000)",
      valueClassName: "text-2xl font-semibold tabular-nums",
    },
    {
      label: scenarioActive
        ? "Modeled exposure plotted"
        : "Locations plotted on map",
      value: formatCount(plottedPoints),
      hint: scenarioActive
        ? "Fuchsia highlights — modeled potential exposure, not confirmed outages"
        : "Premises with valid coordinates in the current response",
      valueClassName: "text-2xl font-semibold tabular-nums",
    },
    {
      label: "Device type",
      value: deviceType ?? "—",
      hint: "From network dependency index",
      valueClassName:
        "text-base font-semibold leading-snug break-words whitespace-normal",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3"
        >
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            {card.label}
          </p>
          <p
            className={`mt-1 text-zinc-50 ${card.valueClassName} ${loading ? "animate-pulse text-zinc-600" : ""}`}
          >
            {loading ? "…" : card.value}
          </p>
          <p className="mt-1 text-[11px] leading-snug text-zinc-600">
            {card.hint}
          </p>
        </div>
      ))}
    </div>
  );
}

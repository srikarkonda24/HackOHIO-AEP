export const GIS_LAYER_ORDER = [
  "primary",
  "secondary",
  "poles",
  "transformers",
  "fuses",
  "switches",
  "reclosers",
  "damage",
  "emergency",
] as const;

export type GisLayerId = (typeof GIS_LAYER_ORDER)[number];

export const GIS_LAYER_STYLE: Record<
  GisLayerId,
  {
    label: string;
    color: string;
    kind: "line" | "circle";
    radius?: number;
    width?: number;
  }
> = {
  primary: { label: "Primary lines", color: "#facc15", kind: "line", width: 1.7 },
  secondary: { label: "Secondary lines", color: "#94a3b8", kind: "line", width: 1.1 },
  poles: { label: "Poles", color: "#d6d3d1", kind: "circle", radius: 2.4 },
  transformers: { label: "Transformers", color: "#4ade80", kind: "circle", radius: 3.6 },
  fuses: { label: "Fuses", color: "#fb923c", kind: "circle", radius: 3.8 },
  switches: { label: "Switches", color: "#c084fc", kind: "circle", radius: 4.4 },
  reclosers: { label: "Reclosers", color: "#f87171", kind: "circle", radius: 6 },
  damage: { label: "Historical damage", color: "#fb7185", kind: "circle", radius: 5.6 },
  emergency: { label: "Emergency facilities", color: "#38bdf8", kind: "circle", radius: 6 },
};

export const GIS_CLICK_PRIORITY: GisLayerId[] = [
  "reclosers",
  "switches",
  "fuses",
  "transformers",
  "damage",
  "emergency",
  "poles",
  "primary",
  "secondary",
];

export function sourceId(layerId: string): string {
  return `gis-${layerId}`;
}

export function renderLayerId(layerId: string): string {
  return `gis-${layerId}-render`;
}

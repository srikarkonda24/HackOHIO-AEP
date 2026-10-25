/**
 * Fixed SVG layout for Level 4 illustrative network (900×500).
 * Coordinates match graph topology; does not alter backend connectivity.
 */

export const DIAGRAM_VIEWBOX = { width: 900, height: 500 } as const;

export const CARD_W = 118;
export const CARD_H = 44;

export interface DiagramPoint {
  x: number;
  y: number;
}

export interface EquipmentCardLayout {
  id: string;
  x: number;
  y: number;
  displayName: string;
  detail: string;
  labelAnchor: "above" | "below";
}

export const DIAGRAM_SOURCE: DiagramPoint = { x: 450, y: 44 };

export const DIAGRAM_SWITCHES = {
  S1: { x: 450, y: 178, label: "Sectionalizer (S1)" },
  S2: { x: 748, y: 248, label: "Tie switch (S2)" },
} as const;

export const DIAGRAM_FACILITIES = [
  { id: "HOSPITAL", x: 88, y: 448, label: "Hospital" },
  { id: "RES1", x: 248, y: 448, label: "Your home" },
  { id: "RES2", x: 450, y: 448, label: "Homes" },
  { id: "FIRE", x: 652, y: 448, label: "Fire station" },
  { id: "RES3", x: 812, y: 448, label: "Homes" },
] as const;

/** Main pole row, branch row, downstream row — generous horizontal spacing */
export const DIAGRAM_EQUIPMENT: EquipmentCardLayout[] = [
  {
    id: "A",
    x: 450,
    y: 108,
    displayName: "Main Pole",
    detail: "Main upstream pole and feed into the neighborhood",
    labelAnchor: "above",
  },
  {
    id: "B",
    x: 88,
    y: 248,
    displayName: "Hospital Line",
    detail: "Hospital branch conductor — hospital out until restored or tied",
    labelAnchor: "below",
  },
  {
    id: "D",
    x: 450,
    y: 248,
    displayName: "Trunk Line",
    detail: "Trunk conductor serving downstream neighborhoods",
    labelAnchor: "below",
  },
  {
    id: "C",
    x: 248,
    y: 368,
    displayName: "Transformer",
    detail: "Transformer on the path to your home (modeled customer)",
    labelAnchor: "below",
  },
  {
    id: "F",
    x: 450,
    y: 368,
    displayName: "Zone 2 transformer",
    detail: "Residential transformer for zone 2",
    labelAnchor: "below",
  },
  {
    id: "E",
    x: 652,
    y: 368,
    displayName: "Switch",
    detail: "Fire station branch switchgear",
    labelAnchor: "below",
  },
  {
    id: "G",
    x: 812,
    y: 368,
    displayName: "Neighborhood Line",
    detail: "Lateral line serving zone 3 homes",
    labelAnchor: "below",
  },
];

/** Orthogonal paths — bus runs at y=218 above branch cards; tie routes above labels */
export const DIAGRAM_WIRES: { d: string; dashed?: boolean; tie?: boolean }[] = [
  { d: "M 450 62 L 450 86" },
  { d: "M 450 130 L 450 154" },
  { d: "M 450 202 L 450 218" },
  { d: "M 147 218 L 753 218" },
  { d: "M 88 218 L 88 226" },
  { d: "M 450 218 L 450 226" },
  { d: "M 748 218 L 748 230" },
  { d: "M 88 270 L 88 424" },
  { d: "M 450 270 L 450 344" },
  { d: "M 248 344 L 248 424" },
  { d: "M 450 344 L 450 424" },
  { d: "M 652 344 L 652 424" },
  { d: "M 812 344 L 812 424" },
  { d: "M 248 390 L 450 390" },
  { d: "M 450 390 L 812 390" },
  { d: "M 748 230 L 748 188 L 88 188 L 88 218", dashed: true, tie: true },
];

export function equipmentCardRect(center: DiagramPoint): {
  x: number;
  y: number;
  w: number;
  h: number;
} {
  return {
    x: center.x - CARD_W / 2,
    y: center.y - CARD_H / 2,
    w: CARD_W,
    h: CARD_H,
  };
}

export function minEquipmentCenterDistance(): number {
  let min = Infinity;
  const pts = DIAGRAM_EQUIPMENT.map((e) => ({ x: e.x, y: e.y }));
  for (let i = 0; i < pts.length; i++) {
    for (let j = i + 1; j < pts.length; j++) {
      const dx = pts[i].x - pts[j].x;
      const dy = pts[i].y - pts[j].y;
      min = Math.min(min, Math.hypot(dx, dy));
    }
  }
  return min;
}

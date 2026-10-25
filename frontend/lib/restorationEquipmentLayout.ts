/** Diagram layout and judge-friendly labels (backend ids A–G unchanged). */

import {
  DIAGRAM_EQUIPMENT,
  type EquipmentCardLayout,
} from "./restorationDiagramLayout";

export const EQUIPMENT_IDS = ["A", "B", "C", "D", "E", "F", "G"] as const;

export type EquipmentId = (typeof EQUIPMENT_IDS)[number];

export interface EquipmentLayout {
  id: EquipmentId;
  x: number;
  y: number;
  displayName: string;
  detail: string;
  labelAnchor: "above" | "below";
}

export const EQUIPMENT_LAYOUT: EquipmentLayout[] = DIAGRAM_EQUIPMENT.map((row) => ({
  id: row.id as EquipmentId,
  x: row.x,
  y: row.y,
  displayName: row.displayName,
  detail: row.detail,
  labelAnchor: row.labelAnchor,
}));

export const EQUIPMENT_BY_ID: Record<EquipmentId, EquipmentLayout> = Object.fromEntries(
  EQUIPMENT_LAYOUT.map((e) => [e.id, e]),
) as Record<EquipmentId, EquipmentLayout>;

export function equipmentDisplayName(componentId: string): string {
  const row = EQUIPMENT_BY_ID[componentId as EquipmentId];
  return row?.displayName ?? componentId;
}

export function isEquipmentId(id: string): id is EquipmentId {
  return (EQUIPMENT_IDS as readonly string[]).includes(id);
}

export type { EquipmentCardLayout };

"use client";

import {
  CARD_H,
  CARD_W,
  DIAGRAM_FACILITIES,
  DIAGRAM_SOURCE,
  DIAGRAM_SWITCHES,
  DIAGRAM_VIEWBOX,
  DIAGRAM_WIRES,
  equipmentCardRect,
} from "@/lib/restorationDiagramLayout";
import {
  EQUIPMENT_LAYOUT,
  type EquipmentLayout,
  isEquipmentId,
} from "@/lib/restorationEquipmentLayout";
import type { PlaybackFrame } from "@/lib/restorationPlayback";

export function RestorationNetworkDiagram({
  damaged,
  frame,
  selectedId,
  onSelect,
  onToggleDamage,
}: {
  damaged: string[];
  frame: PlaybackFrame;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onToggleDamage: (id: string) => void;
}) {
  const detail = selectedId
    ? EQUIPMENT_LAYOUT.find((e) => e.id === selectedId)
    : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <svg
        viewBox={`0 0 ${DIAGRAM_VIEWBOX.width} ${DIAGRAM_VIEWBOX.height}`}
        className="aspect-[900/500] w-full max-h-[min(58vh,500px)] rounded-xl border border-zinc-700/80 bg-gradient-to-b from-zinc-900 to-zinc-950 shadow-inner"
        role="img"
        aria-label="Illustrative distribution network"
      >
        <defs>
          <filter id="crewGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <NetworkWires />

        <SourceNode />

        <SwitchNode
          id="S1"
          x={DIAGRAM_SWITCHES.S1.x}
          y={DIAGRAM_SWITCHES.S1.y}
          label="S1"
        />
        <SwitchNode
          id="S2"
          x={DIAGRAM_SWITCHES.S2.x}
          y={DIAGRAM_SWITCHES.S2.y}
          label="S2"
        />

        {EQUIPMENT_LAYOUT.map((eq) => (
          <EquipmentCard
            key={eq.id}
            layout={eq}
            damaged={damaged.includes(eq.id)}
            frame={frame}
            selected={selectedId === eq.id}
            onSelect={onSelect}
            onToggle={onToggleDamage}
          />
        ))}

        {DIAGRAM_FACILITIES.map((fac) => (
          <FacilityCard
            key={fac.id}
            id={fac.id}
            x={fac.x}
            y={fac.y}
            label={fac.label}
            isOut={frame.outageGroupIds.has(fac.id)}
          />
        ))}
      </svg>

      {detail ? (
        <p className="mt-2 line-clamp-2 text-sm text-zinc-400">
          <span className="font-medium text-zinc-200">{detail.displayName}</span>
          {" — "}
          {detail.detail}
        </p>
      ) : (
        <p className="mt-2 text-sm text-zinc-500">
          Click equipment cards to toggle simulated damage. Outaged buildings turn red; active
          crew work shows a green highlight on the equipment being repaired.
        </p>
      )}
    </div>
  );
}

function NetworkWires() {
  return (
    <g className="pointer-events-none" aria-hidden>
      {DIAGRAM_WIRES.map((seg, i) => (
        <path
          key={i}
          d={seg.d}
          fill="none"
          stroke={seg.tie ? "#64748b" : "#94a3b8"}
          strokeWidth={seg.tie ? 2 : 2.5}
          strokeDasharray={seg.dashed ? "8 6" : undefined}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={seg.tie ? 0.85 : 1}
        />
      ))}
    </g>
  );
}

function SourceNode() {
  const { x, y } = DIAGRAM_SOURCE;
  return (
    <g>
      <circle cx={x} cy={y} r={22} className="fill-amber-950 stroke-amber-500 stroke-[2.5]" />
      <text
        x={x}
        y={y - 30}
        textAnchor="middle"
        className="fill-amber-200/90 text-[13px] font-semibold"
      >
        Utility source
      </text>
      <text x={x} y={y + 5} textAnchor="middle" className="fill-amber-100 text-[11px] font-medium">
        Grid feed
      </text>
    </g>
  );
}

function SwitchNode({
  x,
  y,
  label,
}: {
  id: string;
  x: number;
  y: number;
  label: string;
}) {
  const s = 18;
  return (
    <g>
      <rect
        x={x - s}
        y={y - s}
        width={s * 2}
        height={s * 2}
        rx={4}
        className="fill-slate-900 stroke-slate-500 stroke-2"
      />
      <text x={x} y={y + 4} textAnchor="middle" className="fill-slate-200 text-[11px] font-semibold">
        {label}
      </text>
    </g>
  );
}

export type EquipmentVisualState = "intact" | "damaged" | "awaiting" | "in_progress" | "repaired";

export function equipmentVisualState(
  id: string,
  damaged: boolean,
  frame: PlaybackFrame,
): EquipmentVisualState {
  const repaired = frame.repairedComponentIds.has(id);
  const inProg =
    frame.inProgress?.kind === "repair" && frame.inProgress.componentId === id;

  if (inProg) return "in_progress";
  if (damaged && !repaired) {
    const queueActive =
      frame.repairedComponentIds.size > 0 || frame.inProgress != null;
    if (queueActive) return "awaiting";
    return "damaged";
  }
  if (damaged && repaired) return "repaired";
  return "intact";
}

function equipmentStyles(state: EquipmentVisualState, selected: boolean, damaged: boolean) {
  const ring = selected ? "stroke-amber-300 stroke-[3]" : "stroke-2";
  switch (state) {
    case "in_progress":
      return {
        card: `fill-red-950/90 stroke-red-400 ${ring}`,
        glow: true,
      };
    case "damaged":
      return { card: `fill-red-950 stroke-red-500 ${ring}`, glow: false };
    case "awaiting":
      return { card: `fill-amber-950 stroke-amber-400 ${ring}`, glow: false };
    case "repaired":
    case "intact":
    default:
      return {
        card: `fill-slate-800/90 stroke-slate-500 ${ring} ${damaged ? "" : ""}`,
        glow: false,
      };
  }
}

function EquipmentCard({
  layout,
  damaged,
  frame,
  selected,
  onSelect,
  onToggle,
}: {
  layout: EquipmentLayout;
  damaged: boolean;
  frame: PlaybackFrame;
  selected: boolean;
  onSelect: (id: string | null) => void;
  onToggle: (id: string) => void;
}) {
  const { id, x, y, displayName, labelAnchor } = layout;
  const state = equipmentVisualState(id, damaged, frame);
  const styles = equipmentStyles(state, selected, damaged);
  const rect = equipmentCardRect({ x, y });
  const labelY = labelAnchor === "above" ? rect.y - 8 : rect.y + rect.h + 16;

  return (
    <g>
      {styles.glow ? (
        <>
          <rect
            x={rect.x - 14}
            y={rect.y - 14}
            width={rect.w + 28}
            height={rect.h + 28}
            rx={16}
            className="fill-emerald-400/20 stroke-none"
            filter="url(#crewGlow)"
          />
          <rect
            x={rect.x - 8}
            y={rect.y - 8}
            width={rect.w + 16}
            height={rect.h + 16}
            rx={12}
            className="fill-emerald-500/35 stroke-emerald-300 stroke-[2.5]"
          />
        </>
      ) : null}
      <rect
        x={rect.x}
        y={rect.y}
        width={rect.w}
        height={rect.h}
        rx={10}
        className={styles.card}
      />
      <text
        x={x}
        y={y + 5}
        textAnchor="middle"
        className="pointer-events-none fill-zinc-50 text-[12px] font-semibold"
      >
        {displayName}
      </text>
      {selected ? (
        <text
          x={x}
          y={labelY}
          textAnchor="middle"
          className="pointer-events-none fill-amber-200/90 text-[11px] font-medium"
        >
          {damaged ? "Damaged — click to clear" : "Click to simulate damage"}
        </text>
      ) : null}
      <rect
        x={rect.x}
        y={rect.y}
        width={rect.w}
        height={rect.h}
        rx={10}
        className="cursor-pointer fill-transparent stroke-transparent"
        role="button"
        tabIndex={0}
        aria-label={`${displayName}, ${damaged ? "damaged" : "intact"}. Toggle simulated damage.`}
        aria-pressed={damaged}
        onClick={() => isEquipmentId(id) && onToggle(id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            if (isEquipmentId(id)) onToggle(id);
          }
        }}
        onMouseEnter={() => onSelect(id)}
        onMouseLeave={() => onSelect(null)}
        onFocus={() => onSelect(id)}
        onBlur={() => onSelect(null)}
      />
    </g>
  );
}

function FacilityCard({
  id,
  x,
  y,
  label,
  isOut,
}: {
  id: string;
  x: number;
  y: number;
  label: string;
  isOut: boolean;
}) {
  const isHome = id === "RES1";
  const w = isHome ? 108 : 92;
  const h = 36;
  const rx = 8;

  let cardClass: string;
  let textClass = "fill-zinc-50";
  if (isOut) {
    cardClass = isHome
      ? "fill-red-950/95 stroke-violet-400 stroke-2"
      : "fill-red-950/95 stroke-red-400 stroke-2";
    if (isHome) {
      textClass = "fill-violet-100";
    }
  } else if (isHome) {
    cardClass = "fill-violet-950/90 stroke-violet-400 stroke-2";
    textClass = "fill-violet-50";
  } else {
    cardClass = "fill-amber-950/90 stroke-amber-500/90 stroke-2";
    textClass = "fill-amber-50";
  }

  return (
    <g>
      <rect
        x={x - w / 2}
        y={y - h / 2}
        width={w}
        height={h}
        rx={rx}
        className={cardClass}
      />
      <text
        x={x}
        y={y + 5}
        textAnchor="middle"
        className={`${textClass} text-[12px] font-medium`}
      >
        {label}
      </text>
    </g>
  );
}

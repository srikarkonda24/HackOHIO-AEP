"use client";

import { GIS_LAYER_ORDER, GIS_LAYER_STYLE } from "@/lib/gisStyle";
import type { GisLayerMeta } from "@/lib/types";

interface LayerTogglesProps {
  catalog: GisLayerMeta[];
  visibility: Record<string, boolean>;
  onToggle: (layerId: string, visible: boolean) => void;
}

export function LayerToggles({
  catalog,
  visibility,
  onToggle,
}: LayerTogglesProps) {
  const metaById = new Map(catalog.map((layer) => [layer.layer_id, layer]));

  return (
    <div className="pointer-events-auto absolute right-3 top-12 z-10 w-56 rounded-md border border-zinc-700/80 bg-zinc-950/92 p-3 text-[11px] text-zinc-300 shadow-lg">
      <p className="font-medium uppercase tracking-wide text-zinc-500">
        Infrastructure layers
      </p>
      <ul className="mt-2 space-y-1.5">
        {GIS_LAYER_ORDER.map((id) => {
          const style = GIS_LAYER_STYLE[id];
          const meta = metaById.get(id);
          const count = meta?.record_count;
          return (
            <li key={id}>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={visibility[id] !== false}
                  onChange={(e) => onToggle(id, e.target.checked)}
                  className="accent-amber-400"
                />
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: style.color }}
                />
                <span className="flex-1 text-zinc-200">{style.label}</span>
                {count !== undefined ? (
                  <span className="tabular-nums text-zinc-600">
                    {count.toLocaleString()}
                  </span>
                ) : null}
              </label>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 leading-snug text-zinc-600">
        Dense layers load for the current map view. White stroke = topology
        match to network.db.
      </p>
    </div>
  );
}

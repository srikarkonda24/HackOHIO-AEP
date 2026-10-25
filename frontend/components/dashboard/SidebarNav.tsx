"use client";

const NAV_ITEMS = [
  { id: "operations", label: "Operations", active: true },
  { id: "restoration", label: "Restoration", active: false, soon: true },
  { id: "damage", label: "Damage overlay", active: false, soon: false },
  { id: "concierge", label: "Customer Concierge", active: false, soon: true },
];

export function SidebarNav() {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-5 py-5">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/15 ring-1 ring-amber-500/40">
            <span className="text-sm font-bold text-amber-400">GA</span>
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-zinc-50">
              GridAware
            </p>
            <p className="text-[11px] uppercase tracking-wider text-zinc-500">
              AEP Operations
            </p>
          </div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={!item.active}
            className={`rounded-md px-3 py-2 text-left text-sm transition-colors ${
              item.active
                ? "bg-zinc-800 font-medium text-zinc-100"
                : "cursor-not-allowed text-zinc-600"
            }`}
          >
            {item.label}
            {item.soon ? (
              <span className="ml-2 text-[10px] uppercase text-zinc-600">
                Soon
              </span>
            ) : null}
          </button>
        ))}
      </nav>
      <div className="border-t border-zinc-800 p-4 text-[11px] leading-relaxed text-zinc-600">
        HackOHI/O 2026 · Dependency impact view. Not confirmed outages.
      </div>
    </aside>
  );
}

"use client";

import type { ReactNode } from "react";

interface DashboardLayoutProps {
  header: ReactNode;
  map: ReactNode;
  panel: ReactNode;
}

export function DashboardLayout({ header, map, panel }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-900 text-zinc-100">
      <header className="z-20 shrink-0 border-b border-zinc-800 bg-zinc-950/95 px-4 py-3 backdrop-blur sm:px-6">
        {header}
      </header>
      <div className="relative min-h-0 flex-1">
        {map}
        <aside className="pointer-events-none absolute right-0 top-0 z-10 flex h-full w-full max-w-[360px] flex-col p-3 sm:p-4">
          <div className="pointer-events-auto flex max-h-full flex-col overflow-hidden rounded-lg border border-zinc-700/80 bg-zinc-950/95 shadow-xl backdrop-blur">
            {panel}
          </div>
        </aside>
      </div>
    </div>
  );
}

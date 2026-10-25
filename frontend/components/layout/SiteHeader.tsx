"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertNavBadge } from "@/components/layout/AlertNavBadge";

export function SiteHeader() {
  const path = usePathname();
  const linkClass = (href: string) =>
    `rounded-md px-3 py-1.5 text-sm ${
      path === href || path.startsWith(`${href}/`)
        ? "bg-zinc-800 font-medium text-zinc-100"
        : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
    }`;

  return (
    <header className="border-b border-zinc-800 bg-zinc-950/95">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-50">GridAware</span>
          <span className="hidden text-xs text-zinc-600 sm:inline">AEP Concierge</span>
        </div>
        <nav className="flex gap-1" aria-label="Main">
          <Link href="/prediction" className={linkClass("/prediction")}>
            Outage Prediction
          </Link>
          <Link href="/restoration" className={linkClass("/restoration")}>
            Restoration Simulator
          </Link>
          <Link href="/alerts" className={linkClass("/alerts")}>
            Outage Alerts
            <AlertNavBadge />
          </Link>
        </nav>
      </div>
    </header>
  );
}

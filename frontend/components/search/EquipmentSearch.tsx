"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, searchDevices } from "@/lib/api";
import type { DeviceSearchRow } from "@/lib/types";

interface EquipmentSearchProps {
  selectedDeviceKey: string | null;
  onSelectRow: (row: DeviceSearchRow) => void;
  disableResults?: boolean;
  compact?: boolean;
}

export function EquipmentSearch({
  selectedDeviceKey,
  onSelectRow,
  disableResults = false,
  compact = false,
}: EquipmentSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DeviceSearchRow[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async (q: string) => {
    if (q.trim().length < 2) {
      setResults([]);
      setError(null);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const data = await searchDevices(q.trim(), 25);
      setResults(data.devices);
    } catch (e) {
      setResults([]);
      setError(e instanceof ApiError ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => runSearch(query), 320);
    return () => window.clearTimeout(t);
  }, [query, runSearch]);

  return (
    <div
      className={`flex flex-col border-b border-zinc-800 ${compact ? "p-4" : "p-4"}`}
    >
      <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Search equipment
      </h2>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Device key or location ID…"
        className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-amber-500/60 focus:outline-none focus:ring-1 focus:ring-amber-500/40"
      />
      {!compact ? (
        <p className="mt-1 text-[11px] text-zinc-600">
          Min. 2 characters · searches device_key and location_id
        </p>
      ) : null}

      {searching ? (
        <p className="mt-3 text-sm text-zinc-500">Searching…</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {!searching && !error && query.trim().length >= 2 && results.length === 0 ? (
        <p className="mt-3 text-sm text-zinc-500">No equipment matched.</p>
      ) : null}

      <ul className="mt-2 max-h-52 overflow-y-auto">
        {results.map((row) => {
          const selected = row.device_key === selectedDeviceKey;
          return (
            <li key={row.device_key}>
              <button
                type="button"
                disabled={disableResults}
                onClick={() => onSelectRow(row)}
                className={`relative z-10 w-full rounded-md px-2 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  selected
                    ? "bg-amber-500/10 ring-1 ring-amber-500/30"
                    : "hover:bg-zinc-800/80"
                }`}
              >
                <p className="font-mono text-[11px] text-zinc-400">
                  {row.device_key}
                </p>
                <p className="mt-0.5 text-zinc-200">{row.device_type}</p>
                <p className="mt-0.5 text-xs text-zinc-500">
                  Location {row.location_id}
                </p>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

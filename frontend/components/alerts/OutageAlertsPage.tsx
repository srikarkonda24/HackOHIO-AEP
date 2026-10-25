"use client";

import { useCallback, useEffect, useState } from "react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import {
  getAlertSession,
  markAlertsRead,
  putAlertPreferences,
  resetAlertSession,
} from "@/lib/alertSessionClient";
import { ALERT_TYPE_LABELS, type AlertEvent, type AlertPreferences } from "@/lib/alertTypes";
import { getDemoAlertSessionId, resetDemoAlertSessionId } from "@/lib/demoAlertSession";
import type { AlertSessionResponse } from "@/lib/alertTypes";

export function OutageAlertsPage() {
  const [sessionId, setSessionId] = useState("");
  const [session, setSession] = useState<AlertSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (sid: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAlertSession(sid);
      setSession(data);
    } catch {
      setError("Could not load demo alert session.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const sid = getDemoAlertSessionId();
    setSessionId(sid);
    void refresh(sid);
  }, [refresh]);

  useEffect(() => {
    if (!sessionId) return;
    void markAlertsRead(sessionId).then(setSession).catch(() => undefined);
  }, [sessionId]);

  const updatePrefs = async (patch: Partial<AlertPreferences>) => {
    if (!session) return;
    const next: AlertPreferences = { ...session.preferences, ...patch };
    const data = await putAlertPreferences(sessionId, next);
    setSession(data);
  };

  const onReset = async () => {
    await resetAlertSession(sessionId);
    const newId = resetDemoAlertSessionId();
    setSessionId(newId);
    await refresh(newId);
  };

  const previewEvents = (session?.events ?? []).filter((e) => e.status === "previewed");

  return (
    <div className="flex min-h-full flex-col bg-zinc-900 text-zinc-100">
      <SiteHeader />
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-50">
            Stay informed about your power
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Simulated proactive alerts for the GridAware demo. Not connected to AEP systems.
          </p>
        </header>

        <section className="mt-6 rounded-xl border border-zinc-800 bg-zinc-950/50 p-4">
          <h2 className="text-sm font-medium text-zinc-200">Notification settings</h2>
          <label className="mt-3 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={session?.preferences.notifications_enabled ?? true}
              onChange={(e) => void updatePrefs({ notifications_enabled: e.target.checked })}
            />
            Enable simulated notifications
          </label>
          <fieldset className="mt-3">
            <legend className="text-xs text-zinc-500">Preferred channel (preview only)</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {(["in_app", "sms", "email"] as const).map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => void updatePrefs({ channel: ch })}
                  className={`rounded-md px-3 py-1.5 text-xs capitalize ${
                    session?.preferences.channel === ch
                      ? "bg-amber-600 text-zinc-950"
                      : "border border-zinc-700 text-zinc-400"
                  }`}
                >
                  {ch.replace("_", "-")}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="mt-3 flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={session?.preferences.medium_risk_preparation ?? false}
              onChange={(e) =>
                void updatePrefs({ medium_risk_preparation: e.target.checked })
              }
            />
            Also notify me for MEDIUM storm-risk scenarios
          </label>
          <button
            type="button"
            onClick={() => void onReset()}
            className="mt-4 text-xs text-zinc-500 underline hover:text-zinc-300"
          >
            Reset demo alerts
          </button>
        </section>

        {loading ? (
          <p className="mt-8 text-center text-sm text-zinc-500">Loading inbox…</p>
        ) : null}
        {error ? (
          <p className="mt-6 text-sm text-red-300" role="alert">
            {error}
          </p>
        ) : null}

        <section className="mt-8">
          <h2 className="text-sm font-medium text-zinc-300">Notification inbox</h2>
          {previewEvents.length === 0 && !loading ? (
            <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/40 px-4 py-8 text-center text-sm text-zinc-500">
              <p>No simulated alerts yet.</p>
              <p className="mt-2">
                Run a high-risk storm on{" "}
                <span className="text-zinc-400">Outage Prediction</span>, then simulate damage
                and restoration on <span className="text-zinc-400">Restoration Simulator</span>.
              </p>
            </div>
          ) : (
            <ul className="mt-4 space-y-4">
              {previewEvents.map((ev) => (
                <AlertCard key={ev.event_id} event={ev} />
              ))}
            </ul>
          )}
        </section>

        {session?.disclaimer ? (
          <p className="mt-8 text-xs text-zinc-600">{session.disclaimer}</p>
        ) : null}
      </main>
    </div>
  );
}

function AlertCard({ event }: { event: AlertEvent }) {
  const typeLabel = ALERT_TYPE_LABELS[event.alert_type] ?? "Alert";
  return (
    <li className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-amber-600/90">
            {typeLabel}
          </p>
          <h3 className="mt-1 font-medium text-zinc-100">{event.title}</h3>
        </div>
        <span className="shrink-0 text-[10px] text-zinc-500">
          {new Date(event.timestamp_utc).toLocaleString()}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-zinc-300">{event.body}</p>
      <p className="mt-2 text-xs text-zinc-500">
        <span className="text-zinc-400">Why:</span> {event.trigger_reason}
      </p>
      <ChannelPreview event={event} />
      <p className="mt-2 text-[10px] font-medium text-amber-700/80">{event.delivery_note}</p>
    </li>
  );
}

function ChannelPreview({ event }: { event: AlertEvent }) {
  const label = event.channel_label;
  if (event.channel === "sms") {
    return (
      <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-300">
        SMS preview → {label}: {event.body}
      </div>
    );
  }
  if (event.channel === "email") {
    return (
      <div className="mt-3 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-zinc-300">
        <p className="text-zinc-500">Subject: {event.title}</p>
        <p className="mt-1">{event.body}</p>
      </div>
    );
  }
  return (
    <div className="mt-3 rounded-lg border border-emerald-900/40 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-100/90">
      In-app banner: {event.body}
    </div>
  );
}

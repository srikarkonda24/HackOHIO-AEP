"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getAssistantStatus, postAssistantChat } from "@/lib/api";
import {
  ASSISTANT_SUGGESTED_QUESTIONS,
  type AssistantChatHistoryMessage,
} from "@/lib/assistantTypes";
import type { RiskWeatherInputs } from "@/lib/riskAssessmentTypes";

const WELCOME =
  "Hi — I'm the GridAware AI Outage Assistant. I can explain your scenario-based outage risk and share general storm-prep tips. I don't have live outage or restoration data.";

interface OutageAssistantPanelProps {
  premiseId: string | null;
  serviceAreaLabel: string | null;
  weatherInputs: RiskWeatherInputs;
  /** When false, assistant explains that a risk calculation is needed first. */
  hasRiskAssessment: boolean;
  essentialMedicalEquipment: boolean;
  onEssentialMedicalEquipmentChange: (value: boolean) => void;
}

export function OutageAssistantPanel({
  premiseId,
  serviceAreaLabel,
  weatherInputs,
  hasRiskAssessment,
  essentialMedicalEquipment,
  onEssentialMedicalEquipmentChange,
}: OutageAssistantPanelProps) {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [messages, setMessages] = useState<AssistantChatHistoryMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getAssistantStatus()
      .then((s) => {
        if (cancelled) return;
        setConfigured(s.llm_configured);
        setStatusMessage(s.message);
      })
      .catch(() => {
        if (cancelled) return;
        setConfigured(false);
        setStatusMessage("Could not reach the assistant service.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const canSend =
    configured === true &&
    premiseId &&
    !loading &&
    draft.trim().length > 0;

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || !premiseId || configured !== true) return;
      if (!hasRiskAssessment) {
        setError("Run Calculate Risk first so the assistant can use verified model context.");
        return;
      }
      setError(null);
      setLoading(true);
      setMessages((prev) => [...prev, { role: "user", content: message }]);
      setDraft("");
      try {
        const data = await postAssistantChat({
          message,
          history: messages.slice(-8),
          premise_id: premiseId,
          storm_scenario: weatherInputs,
          essential_medical_equipment: essentialMedicalEquipment,
        });
        setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      } catch (e) {
        const msg =
          e instanceof ApiError
            ? e.message
            : "Something went wrong. Please try again.";
        setError(msg);
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setLoading(false);
      }
    },
    [
      configured,
      essentialMedicalEquipment,
      hasRiskAssessment,
      messages,
      premiseId,
      weatherInputs,
    ],
  );

  const clearConversation = () => {
    setMessages([]);
    setError(null);
    setDraft("");
  };

  const panelBody = (
    <>
      {configured === false ? (
        <div
          className="rounded-lg border border-zinc-700/80 bg-zinc-900/80 px-3 py-2.5 text-sm text-zinc-400"
          role="status"
        >
          AI assistant not configured yet. {statusMessage}
        </div>
      ) : null}

      {serviceAreaLabel && premiseId ? (
        <p className="text-xs text-zinc-500">
          Context: {serviceAreaLabel} · premise {premiseId}
        </p>
      ) : null}

      <div
        ref={scrollRef}
        className="mt-3 max-h-64 min-h-[12rem] flex-1 space-y-3 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 lg:max-h-[22rem]"
        aria-live="polite"
      >
        <ChatBubble role="assistant" content={WELCOME} />
        {messages.map((m, i) => (
          <ChatBubble key={`${m.role}-${i}`} role={m.role} content={m.content} />
        ))}
        {loading ? (
          <p className="text-sm text-zinc-500" role="status">
            <span className="inline-block animate-pulse">Thinking…</span>
          </p>
        ) : null}
      </div>

      {configured === true ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {ASSISTANT_SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              disabled={!premiseId || loading || !hasRiskAssessment}
              onClick={() => void send(q)}
              className="rounded-full border border-zinc-700 px-2.5 py-1 text-[11px] text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 disabled:opacity-40"
            >
              {q}
            </button>
          ))}
        </div>
      ) : null}

      {error ? (
        <p className="mt-2 text-xs text-red-300" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/40 px-3 py-2.5">
        <label className="flex cursor-pointer items-start gap-2 text-sm text-zinc-300">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={essentialMedicalEquipment}
            onChange={(e) => onEssentialMedicalEquipmentChange(e.target.checked)}
          />
          <span>
            I rely on electricity for essential medical or accessibility equipment
          </span>
        </label>
        <p className="mt-1.5 text-[11px] leading-snug text-zinc-500">
          Personalizes assistant guidance only. Does not notify emergency services or
          enroll you in a utility medical-priority program.
        </p>
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
      >
        <label className="sr-only" htmlFor="assistant-input">
          Message
        </label>
        <input
          id="assistant-input"
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={configured !== true || !premiseId || loading}
          placeholder={
            configured === false
              ? "Assistant unavailable"
              : hasRiskAssessment
                ? "Ask about your scenario…"
                : "Calculate risk first…"
          }
          className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 disabled:opacity-50"
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={!canSend}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-zinc-950 hover:bg-amber-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>

      <button
        type="button"
        onClick={clearConversation}
        className="mt-2 text-xs text-zinc-500 underline-offset-2 hover:text-zinc-400 hover:underline"
      >
        Clear conversation
      </button>
    </>
  );

  return (
    <>
      {/* Desktop: sticky side panel */}
      <section
        className="hidden lg:flex lg:max-h-[calc(100vh-8rem)] lg:flex-col lg:rounded-xl lg:border lg:border-zinc-800 lg:bg-zinc-950/50 lg:p-4"
        aria-labelledby="assistant-heading-desktop"
      >
        <h2
          id="assistant-heading-desktop"
          className="text-lg font-semibold text-zinc-50"
        >
          AI Outage Assistant
        </h2>
        {panelBody}
      </section>

      {/* Mobile: collapsible */}
      <section
        className="lg:hidden rounded-xl border border-zinc-800 bg-zinc-950/50"
        aria-labelledby="assistant-heading-mobile"
      >
        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
          aria-expanded={mobileOpen}
        >
          <span id="assistant-heading-mobile" className="font-semibold text-zinc-50">
            AI Outage Assistant
          </span>
          <span className="text-zinc-500">{mobileOpen ? "−" : "+"}</span>
        </button>
        {mobileOpen ? <div className="border-t border-zinc-800 px-4 pb-4">{panelBody}</div> : null}
      </section>
    </>
  );
}

function ChatBubble({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <p
        className={`max-w-[95%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-amber-900/40 text-amber-50"
            : "bg-zinc-800/80 text-zinc-200"
        }`}
      >
        {content}
      </p>
    </div>
  );
}

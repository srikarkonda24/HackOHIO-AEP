"use client";

import { useCallback, useEffect, useState } from "react";
import { evaluateRiskPreparation } from "@/lib/alertSessionClient";
import { getDemoAlertSessionId } from "@/lib/demoAlertSession";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { OutageAssistantPanel } from "@/components/customer/OutageAssistantPanel";
import { StormRiskSimulator } from "@/components/customer/StormRiskSimulator";
import { ApiError, getCustomerNetworkContext } from "@/lib/api";
import {
  hasIncompleteData,
  incompleteDataMessage,
  summarizeNetworkKnowledge,
  summarizeServiceLocation,
} from "@/lib/customerContextSummary";
import { formatCompactLocation } from "@/lib/customerRiskExplanation";
import { EXAMPLE_CUSTOMER_PREMISE_ID } from "@/lib/constants";
import { RISK_DEMO_PRESETS } from "@/lib/riskAssessmentTypes";
import type { CustomerNetworkContext } from "@/lib/networkContextTypes";
import type {
  RiskAssessmentResponse,
  RiskWeatherInputs,
} from "@/lib/riskAssessmentTypes";

type LoadState = "idle" | "loading" | "error" | "ready";

export function CustomerDashboard() {
  const [premiseInput, setPremiseInput] = useState(EXAMPLE_CUSTOMER_PREMISE_ID);
  const [context, setContext] = useState<CustomerNetworkContext | null>(null);
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [techOpen, setTechOpen] = useState(false);
  const [lastAssessment, setLastAssessment] =
    useState<RiskAssessmentResponse | null>(null);
  const [weatherInputs, setWeatherInputs] = useState<RiskWeatherInputs>(
    RISK_DEMO_PRESETS.mild.inputs,
  );
  const [essentialMedicalEquipment, setEssentialMedicalEquipment] = useState(false);

  const load = useCallback(async (premiseId: string) => {
    const id = premiseId.trim();
    if (!id) {
      setError("Enter an anonymized premise ID.");
      setState("error");
      return;
    }
    setState("loading");
    setError(null);
    setContext(null);
    setLastAssessment(null);
    try {
      const data = await getCustomerNetworkContext(id);
      setContext(data);
      setState("ready");
    } catch (e) {
      setState("error");
      if (e instanceof ApiError && e.status === 404) {
        setError("We could not find that premise ID in the network index.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Unable to load your service location. Try again later.");
      }
    }
  }, []);

  const locationLabel = context ? formatCompactLocation(context) : null;

  useEffect(() => {
    if (!lastAssessment || !context) return;
    const w = lastAssessment.weather_inputs;
    void evaluateRiskPreparation(getDemoAlertSessionId(), context.premise_id, {
      max_wind_gust_mph: w.max_wind_gust_mph,
      total_precipitation_in: w.total_precipitation_in,
      min_temperature_f: w.min_temperature_f,
      snowfall_in: w.snowfall_in,
    }).catch(() => undefined);
  }, [lastAssessment, context]);

  return (
    <div className="flex min-h-full flex-col bg-zinc-900 text-zinc-100">
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:py-10">
        <header className="text-center sm:text-left">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-50 sm:text-4xl">
            Will my power go out?
          </h1>
          <p className="mt-3 text-base text-zinc-400">
            See how different storm conditions could affect your electricity.
          </p>
        </header>

        <form
          className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            void load(premiseInput);
          }}
        >
          <label className="flex-1 text-sm">
            <span className="font-medium text-zinc-300">Anonymized premise ID</span>
            <input
              type="text"
              value={premiseInput}
              onChange={(e) => setPremiseInput(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-base text-zinc-100 placeholder:text-zinc-600 focus:border-amber-600/60 focus:outline-none focus:ring-1 focus:ring-amber-600/40"
              placeholder="e.g. 000052580"
              autoComplete="off"
            />
          </label>
          <button
            type="submit"
            disabled={state === "loading"}
            className="rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-medium text-zinc-950 hover:bg-amber-500 disabled:opacity-50"
          >
            {state === "loading" ? "Loading…" : "Load"}
          </button>
        </form>
        <button
          type="button"
          className="mt-2 text-sm text-zinc-500 underline-offset-2 hover:text-zinc-400 hover:underline"
          onClick={() => {
            setPremiseInput(EXAMPLE_CUSTOMER_PREMISE_ID);
            void load(EXAMPLE_CUSTOMER_PREMISE_ID);
          }}
        >
          Use verified example ({EXAMPLE_CUSTOMER_PREMISE_ID})
        </button>

        {state === "loading" ? (
          <p className="mt-6 text-center text-sm text-zinc-500" role="status">
            Looking up your service location…
          </p>
        ) : null}

        {state === "error" && error ? (
          <div
            className="mt-6 rounded-lg border border-red-900/50 bg-red-950/30 px-4 py-3 text-sm text-red-200"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        {state === "ready" && context ? (
          <div className="mt-6 space-y-6">
            {locationLabel ? (
              <p
                className="inline-flex items-center gap-2 rounded-full border border-zinc-700/80 bg-zinc-950/80 px-3 py-1 text-sm text-zinc-300"
                role="status"
              >
                <span className="text-zinc-500" aria-hidden>
                  ●
                </span>
                Service area: {locationLabel}
              </p>
            ) : null}

            {hasIncompleteData(context) && incompleteDataMessage(context) ? (
              <div
                className="rounded-lg border border-amber-900/40 bg-amber-950/20 px-4 py-2.5 text-sm text-amber-100/90"
                role="status"
              >
                {incompleteDataMessage(context)}
              </div>
            ) : null}

            <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_min(22rem,34%)] lg:items-start lg:gap-6">
              <StormRiskSimulator
                premiseId={context.premise_id}
                onAssessmentChange={setLastAssessment}
                onWeatherInputsChange={setWeatherInputs}
              />
              <OutageAssistantPanel
                premiseId={context.premise_id}
                serviceAreaLabel={locationLabel}
                weatherInputs={weatherInputs}
                hasRiskAssessment={lastAssessment !== null}
                essentialMedicalEquipment={essentialMedicalEquipment}
                onEssentialMedicalEquipmentChange={setEssentialMedicalEquipment}
              />
            </div>

            <section className="rounded-lg border border-zinc-800 bg-zinc-950/40">
              <button
                type="button"
                onClick={() => setTechOpen((v) => !v)}
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-zinc-400"
                aria-expanded={techOpen}
              >
                Technical details and methodology
                <span className="text-zinc-600">{techOpen ? "−" : "+"}</span>
              </button>
              {techOpen ? (
                <div className="space-y-5 border-t border-zinc-800 px-4 py-4 text-xs leading-relaxed text-zinc-400">
                  <div>
                    <p className="font-medium text-zinc-500">Service location (indexed)</p>
                    <ul className="mt-2 list-disc pl-4">
                      {summarizeServiceLocation(context).map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="font-medium text-zinc-500">Network context</p>
                    <ul className="mt-2 list-disc pl-4">
                      {summarizeNetworkKnowledge(context).map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                    <p className="mt-2 text-zinc-500">
                      {context.upstream_device_count} indexed upstream equipment
                      associations (unordered).
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-zinc-500">
                      Evidence quality &amp; confidence
                    </p>
                    <p className="mt-2 text-zinc-400">
                      Low/Medium/High reflects relative scenario comparison from
                      historical ERA5 weather and AEP ARCOS equipment-damage records in
                      southwest Virginia—not a calibrated outage probability or
                      statistical confidence percentage. Verified per-customer outage and
                      non-outage outcomes were not available for this model, so evidence
                      quality stays conservative even when risk is High.
                    </p>
                  </div>
                  {context.limitations.length ? (
                    <div>
                      <p className="font-medium text-zinc-500">Data limitations</p>
                      <ul className="mt-2 list-disc pl-4">
                        {context.limitations.map((lim) => (
                          <li key={lim}>{lim}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {context.circuit_identifier_observations.length ? (
                    <div>
                      <p className="font-medium text-zinc-500">
                        Circuit identifier observations (not reconciled)
                      </p>
                      <ul className="mt-2 list-disc pl-4">
                        {context.circuit_identifier_observations.map((o) => (
                          <li key={o.location_n}>
                            Location {o.location_n}:{" "}
                            {Object.keys(o.circuit_ids).join(" vs ")}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {lastAssessment ? (
                    <div className="space-y-4 border-t border-zinc-800 pt-4">
                      <p className="font-medium text-zinc-500">Latest risk assessment</p>
                      {lastAssessment.evidence_quality_customer ? (
                        <p className="text-zinc-400">
                          Evidence quality:{" "}
                          {lastAssessment.evidence_quality_customer.label} —{" "}
                          {lastAssessment.evidence_quality_customer.summary}
                        </p>
                      ) : null}
                      <p className="text-zinc-400">{lastAssessment.explanation}</p>
                      {lastAssessment.applicable_damage_associations.length ? (
                        <>
                          <p className="font-medium text-zinc-500">
                            Historical damage associations
                          </p>
                          <ul className="list-disc pl-4">
                            {lastAssessment.applicable_damage_associations.map((row) => (
                              <li
                                key={`${row.weather_condition}-${row.damage_category}`}
                              >
                                {row.damage_category}: enrichment ≈{" "}
                                {row.enrichment_ratio.toFixed(2)} (
                                {row.matching_damage_date_location_pairs} matched pairs
                                {row.sparse_evidence ? ", sparse sample" : ""})
                              </li>
                            ))}
                          </ul>
                        </>
                      ) : null}
                      {lastAssessment.infrastructure_context_summary.length ? (
                        <>
                          <p className="font-medium text-zinc-500">
                            Infrastructure context summary
                          </p>
                          <ul className="list-disc pl-4">
                            {lastAssessment.infrastructure_context_summary.map((line) => (
                              <li key={line}>{line}</li>
                            ))}
                          </ul>
                        </>
                      ) : null}
                      <p className="font-medium text-zinc-500">Damage-type assumptions</p>
                      <ul className="list-disc pl-4">
                        {Object.entries(
                          lastAssessment.damage_impact_assumptions_context,
                        ).map(([cat, level]) => (
                          <li key={cat}>
                            {cat}: {level}
                          </li>
                        ))}
                      </ul>
                      <pre className="max-h-48 overflow-auto rounded bg-zinc-900 p-2 font-mono text-[10px]">
                        {JSON.stringify(lastAssessment.evidence_quality, null, 2)}
                      </pre>
                      <pre className="max-h-64 overflow-auto rounded bg-zinc-900 p-2 font-mono text-[10px]">
                        {JSON.stringify(lastAssessment, null, 2)}
                      </pre>
                    </div>
                  ) : null}
                  <div>
                    <p className="font-medium text-zinc-500">Network context API response</p>
                    <pre className="mt-2 max-h-64 overflow-auto rounded bg-zinc-900 p-3 font-mono text-[10px] text-zinc-500">
                      {JSON.stringify(context, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : null}
            </section>
          </div>
        ) : null}

        {state === "idle" ? (
          <p className="mt-8 text-center text-sm text-zinc-600">
            Enter a premise ID or use the example to get started.
          </p>
        ) : null}
      </main>
    </div>
  );
}

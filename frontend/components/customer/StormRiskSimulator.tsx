"use client";



import { useCallback, useEffect, useState } from "react";

import { ApiError, postCustomerRiskAssessment } from "@/lib/api";

import {

  buildCustomerRiskExplanation,

  RISK_RESULT_LABEL,

} from "@/lib/customerRiskExplanation";
import { evidenceQualityFromAssessment } from "@/lib/riskEvidenceQuality";

import {

  RISK_DEMO_PRESETS,

  type RelativeRisk,

  type RiskAssessmentResponse,

  type RiskWeatherInputs,

} from "@/lib/riskAssessmentTypes";



const RISK_STYLE: Record<

  RelativeRisk,

  { panel: string; label: string; accent: string }

> = {

  LOW: {

    panel: "border-emerald-800/60 bg-emerald-950/25",

    label: "text-emerald-300",

    accent: "bg-emerald-500/20",

  },

  MEDIUM: {

    panel: "border-amber-800/60 bg-amber-950/25",

    label: "text-amber-200",

    accent: "bg-amber-500/20",

  },

  HIGH: {

    panel: "border-red-800/60 bg-red-950/30",

    label: "text-red-200",

    accent: "bg-red-500/20",

  },

};



interface StormRiskSimulatorProps {

  premiseId: string;

  onAssessmentChange?: (result: RiskAssessmentResponse | null) => void;

  onWeatherInputsChange?: (inputs: RiskWeatherInputs) => void;

}



export function StormRiskSimulator({

  premiseId,

  onAssessmentChange,
  onWeatherInputsChange,

}: StormRiskSimulatorProps) {

  const [inputs, setInputs] = useState<RiskWeatherInputs>(

    RISK_DEMO_PRESETS.mild.inputs,

  );

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [result, setResult] = useState<RiskAssessmentResponse | null>(null);



  useEffect(() => {

    setResult(null);

    onAssessmentChange?.(null);

  }, [premiseId, onAssessmentChange]);

  useEffect(() => {
    onWeatherInputsChange?.(inputs);
  }, [inputs, onWeatherInputsChange]);

  const setField = (key: keyof RiskWeatherInputs, value: number) => {

    setInputs((prev) => ({ ...prev, [key]: value }));

  };



  const applyPreset = (key: keyof typeof RISK_DEMO_PRESETS) => {

    setInputs({ ...RISK_DEMO_PRESETS[key].inputs });

  };



  const calculate = useCallback(async () => {

    setLoading(true);

    setError(null);

    try {

      const data = await postCustomerRiskAssessment(premiseId, inputs);

      setResult(data);

      onAssessmentChange?.(data);

    } catch (e) {

      setResult(null);

      onAssessmentChange?.(null);

      if (e instanceof ApiError) {

        setError(e.message);

      } else {

        setError("Could not calculate risk. Try again later.");

      }

    } finally {

      setLoading(false);

    }

  }, [premiseId, inputs, onAssessmentChange]);



  const customerLines = result ? buildCustomerRiskExplanation(result) : [];
  const evidenceQuality = evidenceQualityFromAssessment(result);



  return (

    <section

      className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-5 sm:p-6"

      aria-labelledby="storm-risk-heading"

    >

      <h2 id="storm-risk-heading" className="text-xl font-semibold text-zinc-50">

        Storm Outage Risk Simulator

      </h2>

      <p className="mt-2 text-sm text-zinc-400">

        Set hypothetical{" "}

        <span className="font-medium text-zinc-300">3-day storm conditions</span>{" "}

        below, then calculate a relative outage-risk level for your area.

      </p>



      <div className="mt-4 flex flex-wrap gap-2">

        {(Object.keys(RISK_DEMO_PRESETS) as Array<keyof typeof RISK_DEMO_PRESETS>).map(

          (key) => (

            <button

              key={key}

              type="button"

              onClick={() => applyPreset(key)}

              className="rounded-md border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-600 hover:bg-zinc-800"

            >

              {RISK_DEMO_PRESETS[key].label}

            </button>

          ),

        )}

      </div>



      <p className="mt-4 text-xs font-medium uppercase tracking-wide text-zinc-500">

        Hypothetical 3-day storm totals

      </p>



      <div className="mt-3 grid gap-5 sm:grid-cols-2">

        <WeatherControl

          label="Maximum wind gust (mph)"

          min={0}

          max={80}

          step={1}

          value={inputs.max_wind_gust_mph}

          onChange={(v) => setField("max_wind_gust_mph", v)}

        />

        <WeatherControl

          label="Total precipitation (inches)"

          min={0}

          max={5}

          step={0.01}

          value={inputs.total_precipitation_in}

          onChange={(v) => setField("total_precipitation_in", v)}

        />

        <WeatherControl

          label="Minimum temperature (°F)"

          min={-10}

          max={90}

          step={1}

          value={inputs.min_temperature_f}

          onChange={(v) => setField("min_temperature_f", v)}

        />

        <WeatherControl

          label="Total snowfall (inches)"

          min={0}

          max={12}

          step={0.1}

          value={inputs.snowfall_in}

          onChange={(v) => setField("snowfall_in", v)}

        />

      </div>



      <button

        type="button"

        onClick={() => void calculate()}

        disabled={loading}

        className="mt-6 w-full rounded-lg bg-amber-600 px-5 py-3 text-sm font-semibold text-zinc-950 hover:bg-amber-500 disabled:opacity-50 sm:w-auto"

      >

        {loading ? "Calculating…" : "Calculate Risk"}

      </button>



      {error ? (

        <p className="mt-4 text-sm text-red-300" role="alert">

          {error}

        </p>

      ) : null}



      {result ? (

        <div

          className={`mt-8 rounded-xl border p-6 sm:p-8 ${RISK_STYLE[result.relative_risk].panel}`}

          role="status"

          aria-live="polite"

        >

          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">

            Relative outage concern

          </p>

          <p

            className={`mt-2 text-4xl font-bold tracking-tight sm:text-5xl ${RISK_STYLE[result.relative_risk].label}`}

          >

            {RISK_RESULT_LABEL[result.relative_risk]}

          </p>

          <div

            className={`mt-4 inline-block rounded-md px-2 py-0.5 text-xs font-semibold text-zinc-300 ${RISK_STYLE[result.relative_risk].accent}`}

          >

            {result.relative_risk}

          </div>

          {evidenceQuality ? (
            <p
              className="mt-4 text-sm text-zinc-400"
              title={evidenceQuality.summary}
            >
              <span className="font-medium text-zinc-300">Evidence quality:</span>{" "}
              {evidenceQuality.label}
              <span className="mt-1 block text-xs leading-snug text-zinc-500">
                {evidenceQuality.summary}
              </span>
            </p>
          ) : null}

          <div className="mt-5 space-y-2 text-base leading-relaxed text-zinc-200">

            {customerLines.map((line) => (

              <p key={line}>{line}</p>

            ))}

          </div>

          <p className="mt-5 text-xs text-zinc-500">

            Scenario-based estimate, not a live forecast or confirmed outage.

          </p>

        </div>

      ) : null}

    </section>

  );

}



function WeatherControl({

  label,

  min,

  max,

  step,

  value,

  onChange,

}: {

  label: string;

  min: number;

  max: number;

  step: number;

  value: number;

  onChange: (v: number) => void;

}) {

  return (

    <label className="block text-sm">

      <span className="font-medium text-zinc-300">{label}</span>

      <input

        type="range"

        min={min}

        max={max}

        step={step}

        value={value}

        onChange={(e) => onChange(Number(e.target.value))}

        className="mt-2 w-full accent-amber-500"

      />

      <input

        type="number"

        min={min}

        max={max}

        step={step}

        value={value}

        onChange={(e) => onChange(Number(e.target.value))}

        className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-zinc-100"

      />

    </label>

  );

}


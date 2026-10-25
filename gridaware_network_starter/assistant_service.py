"""Outage assistant orchestration."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from assistant_context import apply_user_declared_context, build_verified_assistant_context
from llm_provider import LLMProvider, get_llm_provider

SYSTEM_PROMPT = """You are GridAware's AI Outage Assistant for residential and small-business customers.

Rules you MUST follow:
- Explain only using the structured GridAware context provided in each turn. Do not invent outage probabilities, confirmed outages, or restoration times.
- Treat storm inputs as hypothetical scenarios, not live forecasts. Never say power is definitely out or definitely restored.
- Do not change or override the relative_risk level in the context; explain it in plain language.
- Do not perform independent risk calculations or restoration estimates.
- Do not share internal equipment identifiers, circuit IDs, transformer IDs, or precise coordinates.
- Do not reveal sensitive utility network topology or critical-facility locations beyond the general service area given.
- Offer general storm preparation and electrical safety tips when helpful.
- For immediate life-threatening danger (downed lines, fire, medical emergency), tell the user to call 911 and stay away from energized equipment.
- Be concise, friendly, and practical.
"""

MEDICAL_EQUIPMENT_PROMPT = """
The customer checked a box declaring they rely on electricity for essential medical or
accessibility equipment (user-declared; not verified by GridAware). When true:
- Emphasize backup-power planning, battery checks for essential equipment, and a safe
  alternate location if power may be out for an extended period.
- Suggest contacting their equipment provider, healthcare professional, or utility about
  emergency planning when appropriate.
- For immediate life-threatening situations, tell them to call 911.
You MUST NOT: promise prioritized utility restoration; claim enrollment in a medical-
priority program; say GridAware contacts emergency services; guarantee battery duration;
or recommend operating generators indoors.
When the checkbox is false, give normal storm preparation advice without assuming
medical or accessibility needs.
"""


def _format_context_block(ctx: dict[str, Any]) -> str:
    return json.dumps(ctx, indent=2)


def chat_with_assistant(
    con: sqlite3.Connection,
    *,
    user_message: str,
    history: list[dict[str, str]],
    premise_id: str,
    storm_scenario: dict[str, float],
    essential_medical_equipment: bool = False,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    llm = provider if provider is not None else get_llm_provider()
    if llm is None:
        raise AssistantNotConfiguredError()

    ctx = build_verified_assistant_context(
        con,
        premise_id.strip(),
        max_wind_gust_mph=storm_scenario["max_wind_gust_mph"],
        total_precipitation_in=storm_scenario["total_precipitation_in"],
        min_temperature_f=storm_scenario["min_temperature_f"],
        snowfall_in=storm_scenario["snowfall_in"],
    )
    ctx = apply_user_declared_context(
        ctx, essential_medical_equipment=essential_medical_equipment
    )

    system = SYSTEM_PROMPT + "\n" + MEDICAL_EQUIPMENT_PROMPT
    context_message = (
        "Current verified GridAware context (use as sole evidence):\n"
        f"{_format_context_block(ctx)}"
    )

    messages: list[dict[str, str]] = []
    for turn in history[-8:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    reply = llm.complete(
        system_prompt=system + "\n\n" + context_message,
        messages=messages,
    )

    return {
        "reply": reply,
        "assessment_id": ctx["assessment_id"],
        "relative_risk": ctx["relative_risk"],
        "configured": True,
    }


class AssistantNotConfiguredError(Exception):
    pass

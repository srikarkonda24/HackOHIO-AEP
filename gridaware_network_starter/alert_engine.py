"""Deterministic proactive alert rules (no LLM triggers)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from alert_eta import NO_OUTAGE_LABEL, eta_category_for_home
from alert_session_store import AlertSession, append_event
from assistant_context import build_verified_assistant_context


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_id() -> str:
    return str(uuid.uuid4())


def _channel_label(channel: str) -> str:
    return {"sms": "SMS", "email": "Email", "in_app": "In-app"}.get(channel, channel)


def _base_event(
    sess: AlertSession,
    *,
    alert_type: str,
    trigger_reason: str,
    title: str,
    body: str,
    status: str,
    suppression_reason: str | None = None,
    relative_risk: str | None = None,
    eta_category: str | None = None,
    eta_category_previous: str | None = None,
    simulated_time_hours: float | None = None,
) -> dict[str, Any]:
    channel = sess.preferences.channel
    return {
        "event_id": _event_id(),
        "session_id": sess.session_id,
        "premise_id": sess.premise_id,
        "modeled_customer_reference": sess.modeled_customer_group_id,
        "alert_type": alert_type,
        "trigger_reason": trigger_reason,
        "relative_risk": relative_risk,
        "eta_category": eta_category,
        "eta_category_previous": eta_category_previous,
        "channel": channel,
        "channel_label": _channel_label(channel),
        "timestamp_utc": _now_iso(),
        "simulated_time_hours": simulated_time_hours,
        "title": title,
        "body": body,
        "status": status,
        "suppression_reason": suppression_reason,
        "delivery_note": "Not actually sent — simulated preview only.",
        "read": False,
    }


def evaluate_storm_preparation(
    sess: AlertSession,
    con: sqlite3.Connection,
    *,
    premise_id: str,
    max_wind_gust_mph: float,
    total_precipitation_in: float,
    min_temperature_f: float,
    snowfall_in: float,
) -> dict[str, Any]:
    ctx = build_verified_assistant_context(
        con,
        premise_id.strip(),
        max_wind_gust_mph=max_wind_gust_mph,
        total_precipitation_in=total_precipitation_in,
        min_temperature_f=min_temperature_f,
        snowfall_in=snowfall_in,
    )
    risk = ctx["relative_risk"]
    assessment_id = ctx["assessment_id"]
    prefs = sess.preferences

    if assessment_id == sess.last_preparation_assessment_id:
        return {
            "created": False,
            "reason": "duplicate_assessment",
            "assessment_id": assessment_id,
            "relative_risk": risk,
        }

    sess.last_preparation_assessment_id = assessment_id
    sess.premise_id = premise_id.strip()

    eligible = False
    suppression: str | None = None
    if not prefs.notifications_enabled:
        suppression = "Notifications are turned off in demo settings."
    elif risk == "HIGH":
        eligible = True
    elif risk == "MEDIUM" and prefs.medium_risk_preparation:
        eligible = True
    elif risk == "MEDIUM":
        suppression = "Medium-risk preparation alerts are disabled in your preferences."
    elif risk == "LOW":
        suppression = "Low relative risk does not trigger a proactive storm warning by default."

    if risk == "HIGH":
        body = (
            "GridAware: Severe storm conditions indicate HIGH relative outage risk for your "
            "area. Charge essential devices and prepare for possible power interruptions. "
            "(Scenario-based simulation — not a live outage.)"
        )
        title = "Storm preparation recommended"
        trigger = f"HIGH relative outage risk from verified weather scenario (assessment {assessment_id})."
    elif risk == "MEDIUM":
        body = (
            "GridAware: Your scenario shows MEDIUM relative outage risk. Consider charging "
            "devices and reviewing your storm kit. (Scenario-based simulation — not a live outage.)"
        )
        title = "Storm preparation advisory"
        trigger = f"MEDIUM relative outage risk with medium-risk alerts enabled (assessment {assessment_id})."
    else:
        body = ""
        title = "Storm preparation not triggered"
        trigger = f"LOW relative outage risk (assessment {assessment_id})."

    status = "previewed" if eligible else "suppressed"
    event = _base_event(
        sess,
        alert_type="storm_preparation",
        trigger_reason=trigger,
        title=title,
        body=body if eligible else "",
        status=status,
        suppression_reason=suppression,
        relative_risk=risk,
    )
    if eligible:
        append_event(sess, event)
        return {"created": True, "event": event, "relative_risk": risk, "assessment_id": assessment_id}
    if risk == "MEDIUM" and suppression:
        append_event(sess, event)
    return {
        "created": False,
        "event": event if risk == "MEDIUM" else None,
        "relative_risk": risk,
        "assessment_id": assessment_id,
        "suppression_reason": suppression,
    }


def _home_powered(snapshot: dict[str, Any], group_id: str) -> bool:
    out = set(snapshot.get("simulated_outage_group_ids") or [])
    return group_id not in out


def evaluate_restoration_committed(
    sess: AlertSession,
    *,
    sim_run_id: str,
    initial_snapshot: dict[str, Any],
    group_restoration_times: dict[str, float | None],
    modeled_group_id: str,
) -> dict[str, Any]:
    """After a committed restoration simulation run (not damage preview)."""
    tr = sess.restoration
    home_powered_now = _home_powered(initial_snapshot, modeled_group_id)
    created: list[dict[str, Any]] = []

    was_powered = tr.home_was_powered if tr.home_was_powered is not None else True

    # Modeled outage: powered -> unpowered transition on commit
    if was_powered and not home_powered_now:
        if tr.outage_alerted_for_sim != sim_run_id and sess.preferences.notifications_enabled:
            event = _base_event(
                sess,
                alert_type="modeled_outage",
                trigger_reason=(
                    "Your home moved from powered to unpowered in this committed restoration "
                    f"simulation (run {sim_run_id[:8]}…)."
                ),
                title="Simulated outage at your home",
                body=(
                    "GridAware: Your home has lost power in this restoration simulation. "
                    "Crews are assessing the damaged equipment. (Not a real confirmed outage.)"
                ),
                status="previewed",
            )
            append_event(sess, event)
            tr.outage_alerted_for_sim = sim_run_id
            created.append(event)
        elif not sess.preferences.notifications_enabled:
            event = _base_event(
                sess,
                alert_type="modeled_outage",
                trigger_reason="Home lost power in simulation but notifications are disabled.",
                title="Simulated outage (suppressed)",
                body="",
                status="suppressed",
                suppression_reason="Notifications are turned off in demo settings.",
            )
            append_event(sess, event)

    restore_h = group_restoration_times.get(modeled_group_id)
    tr.home_restore_time_hours = (
        float(restore_h) if restore_h is not None and not home_powered_now else None
    )

    eta_cat = eta_category_for_home(
        initially_powered=home_powered_now,
        restoration_hours=restore_h,
    )
    if (
        not home_powered_now
        and eta_cat
        and eta_cat != NO_OUTAGE_LABEL
        and tr.last_eta_category
        and tr.last_eta_category != eta_cat
        and tr.last_sim_run_id
        and sess.preferences.notifications_enabled
    ):
        event = _base_event(
            sess,
            alert_type="eta_update",
            trigger_reason=(
                f"Modeled home restoration window changed from {tr.last_eta_category} to "
                f"{eta_cat} after a new simulation run."
            ),
            title="Restoration estimate updated",
            body=(
                f"GridAware: Your modeled restoration estimate has changed from "
                f"{tr.last_eta_category} to {eta_cat}. (Simulation only — not a guarantee.)"
            ),
            status="previewed",
            eta_category=eta_cat,
            eta_category_previous=tr.last_eta_category,
        )
        append_event(sess, event)
        created.append(event)
    elif (
        not home_powered_now
        and eta_cat
        and tr.last_eta_category == eta_cat
        and tr.last_sim_run_id == sim_run_id
    ):
        pass  # duplicate ETA — no event

    if eta_cat and not home_powered_now:
        tr.last_eta_category = eta_cat

    tr.home_was_powered = home_powered_now
    tr.last_sim_run_id = sim_run_id
    return {"created_events": created, "home_powered": home_powered_now, "eta_category": eta_cat}


def evaluate_restoration_playback(
    sess: AlertSession,
    *,
    sim_run_id: str,
    playback_time_hours: float,
    modeled_group_id: str,
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fire restoration complete when playback reaches backend group_restored time."""
    tr = sess.restoration
    if tr.restored_alerted_for_sim == sim_run_id:
        return {"created": False, "reason": "already_restored_alerted"}
    if not sess.preferences.notifications_enabled:
        return {"created": False, "reason": "notifications_disabled"}

    restore_time: float | None = tr.home_restore_time_hours
    for ev in timeline:
        if ev.get("event") == "group_restored" and ev.get("group_id") == modeled_group_id:
            restore_time = float(ev.get("time_hours", restore_time or 0))
            break

    if restore_time is None:
        return {"created": False, "reason": "no_restore_time"}
    if playback_time_hours + 1e-6 < restore_time:
        return {"created": False, "reason": "playback_before_restore"}

    event = _base_event(
        sess,
        alert_type="power_restored",
        trigger_reason=(
            f"Simulation playback reached the calculated restoration time ({restore_time:.2f} h) "
            f"for your home (group {modeled_group_id})."
        ),
        title="Power restored in simulation",
        body=(
            "GridAware: Your home's power has been restored in this simulation. "
            "(Not a live utility confirmation.)"
        ),
        status="previewed",
        simulated_time_hours=restore_time,
    )
    append_event(sess, event)
    tr.restored_alerted_for_sim = sim_run_id
    return {"created": True, "event": event}


def make_sim_run_id(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]

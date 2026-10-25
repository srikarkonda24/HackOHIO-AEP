"""In-memory demo alert sessions (prototype — not durable across API restarts)."""
from __future__ import annotations

import secrets
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

NotificationChannel = Literal["sms", "email", "in_app"]
AlertType = Literal[
    "storm_preparation",
    "modeled_outage",
    "eta_update",
    "power_restored",
]
AlertStatus = Literal["previewed", "suppressed", "eligible"]


@dataclass
class AlertPreferences:
    notifications_enabled: bool = True
    channel: NotificationChannel = "in_app"
    medium_risk_preparation: bool = False


@dataclass
class RestorationTracking:
    last_sim_run_id: str | None = None
    home_was_powered: bool | None = None
    last_eta_category: str | None = None
    outage_alerted_for_sim: str | None = None
    restored_alerted_for_sim: str | None = None
    home_restore_time_hours: float | None = None


@dataclass
class AlertSession:
    session_id: str
    premise_id: str = "000052580"
    modeled_customer_group_id: str = "RES1"
    preferences: AlertPreferences = field(default_factory=AlertPreferences)
    events: list[dict[str, Any]] = field(default_factory=list)
    restoration: RestorationTracking = field(default_factory=RestorationTracking)
    last_preparation_assessment_id: str | None = None
    read_through_event_id: str | None = None


_lock = threading.Lock()
_sessions: dict[str, AlertSession] = {}


def new_session_id() -> str:
    return secrets.token_urlsafe(16)


def get_or_create_session(session_id: str) -> AlertSession:
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = AlertSession(session_id=session_id)
        return _sessions[session_id]


def reset_session(session_id: str) -> AlertSession:
    with _lock:
        sess = AlertSession(session_id=session_id)
        _sessions[session_id] = sess
        return sess


def session_to_dict(sess: AlertSession) -> dict[str, Any]:
    unread = sum(1 for e in sess.events if e.get("status") == "previewed" and not e.get("read"))
    return {
        "session_id": sess.session_id,
        "premise_id": sess.premise_id,
        "modeled_customer_group_id": sess.modeled_customer_group_id,
        "preferences": {
            "notifications_enabled": sess.preferences.notifications_enabled,
            "channel": sess.preferences.channel,
            "medium_risk_preparation": sess.preferences.medium_risk_preparation,
        },
        "events": list(reversed(sess.events)),
        "unread_count": unread,
        "disclaimer": (
            "Simulated GridAware demo alerts only. Not sent by AEP and not a real outage "
            "notification service."
        ),
    }


def append_event(sess: AlertSession, event: dict[str, Any]) -> dict[str, Any]:
    sess.events.append(event)
    return event


def deep_copy_session(sess: AlertSession) -> AlertSession:
    return deepcopy(sess)

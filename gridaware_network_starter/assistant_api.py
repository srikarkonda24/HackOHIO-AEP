"""Customer AI outage assistant API."""
from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from assistant_service import AssistantNotConfiguredError, chat_with_assistant
from llm_provider import configured_model_name, is_llm_configured

router = APIRouter(prefix="/assistant", tags=["assistant"])

_db_path: str | None = None


def configure(db_path: str) -> APIRouter:
    global _db_path
    _db_path = db_path
    return router


def _connect() -> sqlite3.Connection:
    if not _db_path:
        raise HTTPException(status_code=503, detail="Assistant API not configured")
    con = sqlite3.connect(_db_path)
    con.row_factory = sqlite3.Row
    return con


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=4000)]


class StormScenarioInputs(BaseModel):
    max_wind_gust_mph: Annotated[float, Field(ge=0, le=150)]
    total_precipitation_in: Annotated[float, Field(ge=0, le=30)]
    min_temperature_f: Annotated[float, Field(ge=-60, le=120)]
    snowfall_in: Annotated[float, Field(ge=0, le=50)]


class AssistantChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=10)
    premise_id: Annotated[str, Field(min_length=1, max_length=64)]
    storm_scenario: StormScenarioInputs
    essential_medical_equipment: bool = False


@router.get("/status")
def get_assistant_status():
    ready = is_llm_configured()
    return {
        "llm_configured": ready,
        "provider": "google_gemini",
        "model": configured_model_name() if ready else None,
        "message": (
            "AI assistant ready."
            if ready
            else "AI assistant not configured yet. Set GEMINI_API_KEY on the API server."
        ),
    }


@router.post("/chat")
def post_assistant_chat(body: AssistantChatRequest):
    if not is_llm_configured():
        raise HTTPException(
            status_code=503,
            detail="AI assistant not configured yet. Set GEMINI_API_KEY on the API server.",
        )
    with _connect() as con:
        try:
            result = chat_with_assistant(
                con,
                user_message=body.message.strip(),
                history=[m.model_dump() for m in body.history],
                premise_id=body.premise_id.strip(),
                storm_scenario=body.storm_scenario.model_dump(),
                essential_medical_equipment=body.essential_medical_equipment,
            )
        except AssistantNotConfiguredError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Premise not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Assistant could not read network data for this premise. "
                    "Ensure the API is using network.db with sqlite Row support."
                ),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "The assistant encountered an unexpected server error. "
                    "Please try again."
                ),
            ) from exc
    return result

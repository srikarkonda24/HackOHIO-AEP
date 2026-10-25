"""LLM provider adapter — Google Gemini via OpenAI-compatible REST."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Protocol

from openai import APIStatusError, OpenAI

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# Verified against live model list for typical AI Studio keys (Oct 2026).
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"

# Fallback order when the primary model is unavailable or overloaded.
_FLASH_MODEL_FALLBACKS: tuple[str, ...] = (
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
)


class LLMProvider(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str: ...


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def is_llm_configured() -> bool:
    return bool(_gemini_api_key())


def _normalize_model_id(model_id: str) -> str:
    mid = model_id.strip()
    if mid.startswith("models/"):
        mid = mid[len("models/") :]
    return mid


def configured_model_name() -> str:
    explicit = os.getenv("GEMINI_MODEL", "").strip()
    if explicit:
        return _normalize_model_id(explicit)
    return DEFAULT_GEMINI_MODEL


def _model_candidates(preferred: str) -> list[str]:
    preferred = _normalize_model_id(preferred)
    ordered: list[str] = [preferred]
    for mid in _FLASH_MODEL_FALLBACKS:
        if mid not in ordered:
            ordered.append(mid)
    return ordered


@lru_cache(maxsize=1)
def _listed_model_ids(api_key: str) -> frozenset[str]:
    client = OpenAI(api_key=api_key, base_url=GEMINI_OPENAI_BASE_URL)
    try:
        page = client.models.list()
        ids: set[str] = set()
        for model in page.data:
            raw = getattr(model, "id", "") or ""
            ids.add(_normalize_model_id(raw))
        return frozenset(ids)
    except Exception:
        return frozenset()


def _filter_to_listed(candidates: list[str], api_key: str) -> list[str]:
    listed = _listed_model_ids(api_key)
    if not listed:
        return candidates
    filtered = [c for c in candidates if c in listed]
    return filtered or candidates


def _redact_secrets(text: str, api_key: str) -> str:
    out = text
    if api_key:
        out = out.replace(api_key, "[REDACTED]")
    out = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", out)
    return out


def _extract_status_code(exc: Exception) -> int | None:
    if isinstance(exc, APIStatusError):
        return exc.status_code
    code = getattr(exc, "status_code", None)
    return int(code) if isinstance(code, int) else None


def _friendly_gemini_error(status: int | None, raw: str, api_key: str) -> str:
    detail = _redact_secrets(raw, api_key)
    if status == 401 or status == 403:
        return (
            "Gemini rejected the API key (unauthorized). "
            "Check GEMINI_API_KEY on the API server."
        )
    if status == 404:
        return (
            "The configured Gemini model is not available for this API key. "
            "Set GEMINI_MODEL to a supported Flash model (for example gemini-3.1-flash-lite)."
        )
    if status == 429:
        return (
            "Gemini rate limit or quota exceeded. Wait a moment and try again, "
            "or review billing/quota in Google AI Studio."
        )
    if status == 400:
        return f"Gemini rejected the request (invalid input). {detail[:240]}"
    if status == 503:
        return (
            "Gemini is temporarily overloaded for the selected model. "
            "Please try again in a few seconds."
        )
    if status is not None:
        return f"Gemini API error ({status}): {detail[:320]}"
    return f"Gemini assistant request failed: {detail[:320]}"


def _format_provider_error(exc: Exception, api_key: str) -> str:
    status = _extract_status_code(exc)
    raw = exc.message if isinstance(exc, APIStatusError) and exc.message else str(exc)
    return _friendly_gemini_error(status, raw, api_key)


def _should_try_next_model(exc: Exception) -> bool:
    status = _extract_status_code(exc)
    return status in (404, 503, 429)


class GeminiChatProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._preferred_model = _normalize_model_id(model)
        self._client = OpenAI(
            api_key=api_key,
            base_url=GEMINI_OPENAI_BASE_URL,
            timeout=90.0,
            max_retries=0,
        )

    def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        candidates = _filter_to_listed(
            _model_candidates(self._preferred_model),
            self._api_key,
        )
        last_error: Exception | None = None
        payload_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        for model_id in candidates:
            try:
                response = self._client.chat.completions.create(
                    model=model_id,
                    messages=payload_messages,
                    temperature=0.3,
                )
                content = response.choices[0].message.content
                return (content or "").strip()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if _should_try_next_model(exc) and model_id != candidates[-1]:
                    continue
                break

        assert last_error is not None
        raise RuntimeError(_format_provider_error(last_error, self._api_key)) from last_error


def get_llm_provider() -> LLMProvider | None:
    api_key = _gemini_api_key()
    if not api_key:
        return None
    return GeminiChatProvider(api_key, configured_model_name())

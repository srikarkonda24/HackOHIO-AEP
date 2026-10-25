"""LLM provider configuration tests."""
import pytest

from llm_provider import (
    DEFAULT_GEMINI_MODEL,
    GeminiChatProvider,
    _format_provider_error,
    _friendly_gemini_error,
    _model_candidates,
    configured_model_name,
    is_llm_configured,
)


@pytest.fixture(autouse=True)
def clear_keys(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


def test_default_gemini_flash_model():
    assert DEFAULT_GEMINI_MODEL == "gemini-3.1-flash-lite"


def test_is_llm_configured_with_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abc123")
    assert is_llm_configured() is True


def test_gemini_model_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    assert configured_model_name() == "gemini-3.6-flash"


def test_model_candidates_include_fallbacks():
    names = _model_candidates("gemini-3.8-flash")
    assert names[0] == "gemini-3.8-flash"
    assert "gemini-3.1-flash-lite" in names


def test_friendly_error_503():
    msg = _friendly_gemini_error(503, "high demand", "")
    assert "overloaded" in msg.lower() or "try again" in msg.lower()


def test_friendly_error_401():
    msg = _friendly_gemini_error(401, "invalid", "")
    assert "API key" in msg


def test_error_message_redacts_api_key():
    msg = _format_provider_error(
        RuntimeError("failed with AIzaSyDeadBeef1234567890abcdef"),
        "AIzaSyDeadBeef1234567890abcdef",
    )
    assert "AIzaSy" not in msg
    assert "[REDACTED]" in msg


def test_gemini_provider_falls_back_on_503(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    provider = GeminiChatProvider("test-key", "gemini-3.8-flash")
    calls: list[str] = []

    class FakeCompletions:
        def create(self, **kwargs):
            model = kwargs["model"]
            calls.append(model)
            if model == "gemini-3.8-flash":
                err = RuntimeError("high demand")
                err.status_code = 503  # type: ignore[attr-defined]
                raise err
            return type(
                "Resp",
                (),
                {
                    "choices": [
                        type(
                            "C",
                            (),
                            {"message": type("M", (), {"content": "Hello from lite"})()},
                        )()
                    ]
                },
            )()

    provider._client = type("Cl", (), {"chat": type("Ch", (), {"completions": FakeCompletions()})()})()
    # Force candidate list for deterministic test
    monkeypatch.setattr(
        "llm_provider._filter_to_listed",
        lambda candidates, _key: ["gemini-3.8-flash", "gemini-3.1-flash-lite"],
    )
    text = provider.complete(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])
    assert text == "Hello from lite"
    assert calls == ["gemini-3.8-flash", "gemini-3.1-flash-lite"]

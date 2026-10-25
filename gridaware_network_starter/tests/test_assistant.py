"""AI outage assistant API tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import app

DB = Path(__file__).resolve().parents[1] / "network.db"
PID = "000052580"
MILD = {
    "max_wind_gust_mph": 15,
    "total_precipitation_in": 0.02,
    "min_temperature_f": 58,
    "snowfall_in": 0,
}

pytestmark = pytest.mark.skipif(not DB.exists(), reason="network.db not present")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_assistant_status_unconfigured(client: TestClient):
    r = client.get("/assistant/status")
    assert r.status_code == 200
    body = r.json()
    assert body["llm_configured"] is False
    assert body["provider"] == "google_gemini"
    assert "not configured" in body["message"].lower()
    assert "GEMINI_API_KEY" in body["message"]
    assert "AIza" not in r.text


def test_assistant_status_configured(monkeypatch, client: TestClient):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    r = client.get("/assistant/status")
    body = r.json()
    assert body["llm_configured"] is True
    assert body["provider"] == "google_gemini"
    assert body["model"] == "gemini-3.1-flash-lite"
    assert "test-gemini-key" not in r.text


def test_openai_key_does_not_configure_assistant(client: TestClient, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-old-key")
    r = client.get("/assistant/status")
    assert r.json()["llm_configured"] is False


def test_assistant_chat_unconfigured(client: TestClient):
    r = client.post(
        "/assistant/chat",
        json={
            "message": "Why is my risk high?",
            "history": [],
            "premise_id": PID,
            "storm_scenario": MILD,
        },
    )
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


def test_assistant_chat_empty_message_rejected(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    r = client.post(
        "/assistant/chat",
        json={
            "message": "",
            "history": [],
            "premise_id": PID,
            "storm_scenario": MILD,
        },
    )
    assert r.status_code == 422


def test_assistant_chat_unknown_premise(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    class MockProvider:
        def complete(self, *, system_prompt: str, messages: list) -> str:
            return "ok"

    monkeypatch.setattr("assistant_service.get_llm_provider", lambda: MockProvider())
    r = client.post(
        "/assistant/chat",
        json={
            "message": "Hello",
            "history": [],
            "premise_id": "999999999",
            "storm_scenario": MILD,
        },
    )
    assert r.status_code == 404


def test_assistant_chat_uses_backend_risk_context(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    captured: dict = {}

    class MockProvider:
        def complete(self, *, system_prompt: str, messages: list) -> str:
            captured["system"] = system_prompt
            captured["messages"] = messages
            return "Stay prepared and monitor local alerts."

    monkeypatch.setattr("assistant_service.get_llm_provider", lambda: MockProvider())
    r = client.post(
        "/assistant/chat",
        json={
            "message": "What should I do before the storm?",
            "history": [],
            "premise_id": PID,
            "storm_scenario": MILD,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] is True
    assert body["relative_risk"] in ("LOW", "MEDIUM", "HIGH")
    assert "assessment_id" in body
    assert "Stay prepared" in body["reply"]
    assert "test-gemini-key" not in r.text
    assert '"relative_risk"' in captured["system"]
    assert PID in captured["system"]


def test_assistant_includes_medical_context_when_requested(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    captured: dict = {}

    class MockProvider:
        def complete(self, *, system_prompt: str, messages: list) -> str:
            captured["system"] = system_prompt
            return "Prepare backup power and check device batteries."

    monkeypatch.setattr("assistant_service.get_llm_provider", lambda: MockProvider())
    r = client.post(
        "/assistant/chat",
        json={
            "message": "What should I do before the storm?",
            "history": [],
            "premise_id": PID,
            "storm_scenario": MILD,
            "essential_medical_equipment": True,
        },
    )
    assert r.status_code == 200
    assert "essential_medical_or_accessibility_equipment" in captured["system"]
    assert "true" in captured["system"].lower()


def test_assistant_response_never_includes_api_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-key-value")

    class MockProvider:
        def complete(self, *, system_prompt: str, messages: list) -> str:
            return "Safe reply."

    monkeypatch.setattr("assistant_service.get_llm_provider", lambda: MockProvider())
    r = client.post(
        "/assistant/chat",
        json={
            "message": "Hi",
            "history": [],
            "premise_id": PID,
            "storm_scenario": MILD,
        },
    )
    assert r.status_code == 200
    assert "super-secret" not in r.text

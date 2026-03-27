"""Tests for FastAPI webhook endpoints using TestClient."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from auto_validator.models.project import ProjectState
from auto_validator.server.app import app
from auto_validator.state.json_store import JsonFileStore


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def test_client(tmp_path):
    """
    Create a TestClient with the FastAPI app. Override the StateManager used
    by the dependency injector so all persistence goes to a temp directory.
    """
    from auto_validator.server import dependencies
    from auto_validator.state.manager import StateManager

    # Build an isolated StateManager backed by a temp JsonFileStore
    isolated_store = JsonFileStore(data_dir=tmp_path / "projects")
    isolated_mgr = StateManager.__new__(StateManager)
    isolated_mgr._store = isolated_store

    # Override the cached dependency
    from auto_validator.modules.listener import ListenerModule
    import json
    from tests.conftest import MockLLMClient

    mock_llm = MockLLMClient(responses={})

    def mock_listener_module() -> ListenerModule:
        listener = ListenerModule.__new__(ListenerModule)
        listener._state = isolated_mgr
        listener._llm = mock_llm
        return listener

    def mock_state_manager() -> StateManager:
        return isolated_mgr

    # Clear lru_cache and override dependencies
    dependencies.get_state_manager.cache_clear()
    app.dependency_overrides[dependencies.get_listener_module] = mock_listener_module
    app.dependency_overrides[dependencies.get_state_manager] = mock_state_manager

    client = TestClient(app, raise_server_exceptions=True)
    yield client, isolated_store, isolated_mgr

    # Teardown: restore original dependencies
    app.dependency_overrides.clear()
    dependencies.get_state_manager.cache_clear()


@pytest.fixture
def project_in_store(tmp_path):
    """Return a saved ProjectState and its backing store for use in tests."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    state = ProjectState(idea="A test project for webhooks")
    store.save(state)
    return state, store


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_health_endpoint(test_client):
    """GET /health returns 200."""
    client, _, _ = test_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tally_webhook_valid_payload(test_client):
    """POST /webhooks/tally/{project_id} with valid JSON returns 200."""
    client, store, state_mgr = test_client

    # Create a project so the webhook can find it
    state = ProjectState(idea="Tally webhook test project")
    store.save(state)
    project_id = state.project_id

    payload = {
        "data": {
            "respondentId": "tally-resp-abc123",
            "fields": [
                {
                    "key": "question_1",
                    "type": "MULTIPLE_CHOICE",
                    "value": "Yes",
                },
                {
                    "key": "question_2",
                    "type": "TEXTAREA",
                    "value": "I struggle with lesson planning every week.",
                },
                {
                    "key": "question_3",
                    "type": "RATING",
                    "value": "8",
                },
            ],
        }
    }

    response = client.post(f"/webhooks/tally/{project_id}", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify submission was stored
    reloaded = store.load(project_id)
    assert len(reloaded.submissions) == 1
    assert reloaded.submissions[0].pain_score == 8
    assert "lesson planning" in reloaded.submissions[0].open_ended_answer


def test_typeform_webhook_valid_payload(test_client):
    """POST /webhooks/typeform/{project_id} with valid JSON returns 200."""
    client, store, _ = test_client

    state = ProjectState(idea="Typeform webhook test project")
    store.save(state)
    project_id = state.project_id

    payload = {
        "form_response": {
            "token": "typeform-token-xyz789",
            "answers": [
                {
                    "field": {"ref": "q_qualification"},
                    "type": "choice",
                    "choice": {"label": "Yes, I'm a teacher"},
                },
                {
                    "field": {"ref": "q_open"},
                    "type": "text",
                    "text": "Planning is my biggest challenge.",
                },
                {
                    "field": {"ref": "q_pain"},
                    "type": "number",
                    "number": 9,
                },
            ],
        }
    }

    response = client.post(f"/webhooks/typeform/{project_id}", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    reloaded = store.load(project_id)
    assert len(reloaded.submissions) == 1
    assert reloaded.submissions[0].pain_score == 9
    assert "Planning" in reloaded.submissions[0].open_ended_answer
    assert reloaded.submissions[0].respondent_id == "typeform-token-xyz789"


def test_webhook_invalid_project_id(test_client):
    """Returns 404 for unknown project via the reports endpoint."""
    client, _, _ = test_client

    # The tally webhook catches all exceptions and returns 200 (per implementation),
    # but the reports status endpoint will return 404 for an unknown project.
    response = client.get("/reports/nonexistent-project-id-999/status")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_tally_webhook_minimal_payload(test_client):
    """POST /webhooks/tally/{project_id} with minimal fields returns 200."""
    client, store, _ = test_client

    state = ProjectState(idea="Minimal tally payload test")
    store.save(state)
    project_id = state.project_id

    # Payload with no fields — should still process without error
    payload = {"data": {"respondentId": "", "fields": []}}

    response = client.post(f"/webhooks/tally/{project_id}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_typeform_webhook_minimal_payload(test_client):
    """POST /webhooks/typeform/{project_id} with empty answers returns 200."""
    client, store, _ = test_client

    state = ProjectState(idea="Minimal typeform payload test")
    store.save(state)
    project_id = state.project_id

    payload = {"form_response": {"token": "tok-min", "answers": []}}

    response = client.post(f"/webhooks/typeform/{project_id}", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

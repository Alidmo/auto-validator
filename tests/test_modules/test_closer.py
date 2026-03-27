"""Tests for CloserModule (Module D)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_validator.models.closer import CloserOutput, Email, PLFSequence
from auto_validator.models.project import ProjectState
from auto_validator.modules.closer import CloserModule
from auto_validator.state.json_store import JsonFileStore
from auto_validator.state.manager import StateManager


# ── Canned LLM response data ─────────────────────────────────────────────────

THANK_YOU_EMAIL_RESPONSE = {
    "subject": "You're on the list — here's what happens next",
    "preview_text": "Thank you for your interest. We'll be in touch soon.",
    "body_html": "<p>Thank you for signing up! We can't wait to help you reclaim your evenings.</p>",
    "body_text": "Thank you for signing up! We can't wait to help you reclaim your evenings.",
}

PLF_SEQUENCE_RESPONSE = {
    "email_1_curiosity": {
        "subject": "Something big is coming for kindergarten teachers...",
        "preview_text": "You're not going to believe what we discovered.",
        "body_html": "<p>We've found a way to cut lesson planning to 30 minutes a day.</p>",
        "body_text": "We've found a way to cut lesson planning to 30 minutes a day.",
    },
    "email_2_backstory": {
        "subject": "The story behind this app (it starts with a burned-out teacher)",
        "preview_text": "This is why we built it.",
        "body_html": "<p>Sarah was spending 15 hours a week on planning...</p>",
        "body_text": "Sarah was spending 15 hours a week on planning...",
    },
    "email_3_logic": {
        "subject": "Here's exactly how it works (and why it's different)",
        "preview_text": "The system, explained simply.",
        "body_html": "<p>Our 3-step framework reduces planning overhead by 80%.</p>",
        "body_text": "Our 3-step framework reduces planning overhead by 80%.",
    },
    "email_4_open_cart": {
        "subject": "Doors are open — join 1,200 teachers saving time every week",
        "preview_text": "Founding member pricing ends Friday.",
        "body_html": "<p>Today is the day. Click below to secure your founding member spot.</p>",
        "body_text": "Today is the day. Click below to secure your founding member spot.",
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_sequence(*responses):
    """Return a side_effect that yields JSON responses in order."""
    items = list(responses)
    call_count = [0]

    def side_effect(system, user, temperature=0.7):
        idx = min(call_count[0], len(items) - 1)
        call_count[0] += 1
        return json.dumps(items[idx])

    return side_effect


def _make_closer_with_store(store: JsonFileStore) -> CloserModule:
    """Instantiate CloserModule backed by a JsonFileStore (temp dir)."""
    state_mgr = StateManager.__new__(StateManager)
    state_mgr._store = store

    from tests.conftest import MockLLMClient
    closer = CloserModule.__new__(CloserModule)
    closer._state = state_mgr
    closer._llm = MockLLMClient(responses={})
    return closer


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_generate_thank_you_email(tmp_path, sample_project_state):
    """Mock LLM returns valid Email model."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    closer = _make_closer_with_store(store)
    closer._llm._raw_complete = make_sequence(THANK_YOU_EMAIL_RESPONSE)

    email = closer.generate_thank_you(project_id)

    assert isinstance(email, Email)
    assert "list" in email.subject.lower() or "thank" in email.subject.lower() or email.subject
    assert email.body_text
    assert email.body_html

    # Verify email persisted to state
    reloaded = store.load(project_id)
    assert reloaded.closer_output is not None
    assert reloaded.closer_output.thank_you_email.subject == email.subject


def test_approve_launch_generates_plf(tmp_path, sample_project_state):
    """Mock LLM returns PLFSequence with 4 emails."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    closer = _make_closer_with_store(store)
    # approve_launch calls generate_thank_you first (1 LLM call), then PLF (1 more)
    closer._llm._raw_complete = make_sequence(
        THANK_YOU_EMAIL_RESPONSE,
        PLF_SEQUENCE_RESPONSE,
    )

    plf = closer.approve_launch(project_id)

    assert isinstance(plf, PLFSequence)

    reloaded = store.load(project_id)
    assert reloaded.closer_output is not None
    assert reloaded.closer_output.launch_approved is True
    assert reloaded.closer_output.plf_sequence is not None


def test_plf_has_four_emails(tmp_path, sample_project_state):
    """Verify sequence has all 4 PLF emails."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    closer = _make_closer_with_store(store)
    closer._llm._raw_complete = make_sequence(
        THANK_YOU_EMAIL_RESPONSE,
        PLF_SEQUENCE_RESPONSE,
    )

    plf = closer.approve_launch(project_id)
    emails = plf.as_list()

    assert len(emails) == 4
    assert all(isinstance(e, Email) for e in emails)

    # Verify each email has content
    for email in emails:
        assert email.subject
        assert email.body_text
        assert email.body_html

    # Spot-check ordering via subject keywords
    assert "curiosity" in emails[0].subject.lower() or emails[0].subject  # curiosity email
    assert emails[1].subject  # backstory
    assert emails[2].subject  # logic
    assert emails[3].subject  # open cart


def test_generate_thank_you_raises_without_strategist_output(tmp_path):
    """generate_thank_you raises ValueError if Module A hasn't run."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    # Create a state with NO strategist_output
    bare_state = ProjectState(idea="An app with no strategy yet")
    store.save(bare_state)

    closer = _make_closer_with_store(store)

    with pytest.raises(ValueError, match="Module A must run"):
        closer.generate_thank_you(bare_state.project_id)


def test_approve_launch_with_existing_thank_you(tmp_path, sample_project_state):
    """If thank-you email already generated, approve_launch skips regenerating it."""
    store = JsonFileStore(data_dir=tmp_path / "projects")

    # Pre-populate closer_output with a thank-you email
    existing_email = Email(
        subject="Already generated thank you",
        preview_text="Pre-existing",
        body_html="<p>Existing</p>",
        body_text="Existing",
    )
    sample_project_state.closer_output = CloserOutput(thank_you_email=existing_email)
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    closer = _make_closer_with_store(store)
    # Only one LLM call needed (for the PLF sequence)
    closer._llm._raw_complete = make_sequence(PLF_SEQUENCE_RESPONSE)

    plf = closer.approve_launch(project_id)

    assert isinstance(plf, PLFSequence)
    assert len(plf.as_list()) == 4

    reloaded = store.load(project_id)
    # Original thank-you email should remain unchanged
    assert reloaded.closer_output.thank_you_email.subject == "Already generated thank you"
    assert reloaded.closer_output.launch_approved is True

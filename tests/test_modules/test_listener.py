"""Tests for ListenerModule (Module C)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_validator.models.listener import (
    InsightBucket,
    PivotSignal,
    PivotSignalType,
    QuizSubmission,
    WeeklyReport,
)
from auto_validator.models.project import ProjectState
from auto_validator.modules.listener import ListenerModule
from auto_validator.state.json_store import JsonFileStore
from auto_validator.state.manager import StateManager


# ── Canned LLM response data ─────────────────────────────────────────────────

EXTRACT_INSIGHTS_RESPONSE = {
    "buckets": [
        {
            "label": "Time overload",
            "answer_count": 15,
            "percentage": 60.0,
            "representative_quotes": ["I spend every Sunday planning", "No time for family"],
            "sentiment": "negative",
        },
        {
            "label": "Lack of resources",
            "answer_count": 10,
            "percentage": 40.0,
            "representative_quotes": ["Can't find good materials"],
            "sentiment": "negative",
        },
    ],
    "pivot_signals": [
        {
            "signal_type": "price",
            "confidence": 0.3,
            "description": "A few respondents mentioned cost concerns.",
            "recommended_action": "Test a lower price point or freemium tier.",
        }
    ],
}

REPORT_TEXT_RESPONSE = {
    "top_pain_point": "Teachers spend too much time on Sunday lesson planning",
    "recommendation_text": (
        "Your validation data is strong. Focus on the time-saving angle and "
        "launch a beta cohort of 50 teachers."
    ),
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_submission(project_id: str, pain_score: int = 7, answer: str = "I hate planning") -> QuizSubmission:
    return QuizSubmission(
        project_id=project_id,
        respondent_id="resp-001",
        answers={"q1": "Yes", "q2": pain_score},
        open_ended_answer=answer,
        pain_score=pain_score,
        qualified=True,
        submitted_at="2026-03-27T10:00:00+00:00",
    )


def make_sequence(*responses):
    """Return a side_effect that yields JSON responses in order."""
    items = list(responses)
    call_count = [0]

    def side_effect(system, user, temperature=0.7):
        idx = min(call_count[0], len(items) - 1)
        call_count[0] += 1
        return json.dumps(items[idx])

    return side_effect


def _make_listener_with_store(store: JsonFileStore) -> ListenerModule:
    """Instantiate a ListenerModule backed by a real JsonFileStore (temp dir)."""
    state_mgr = StateManager.__new__(StateManager)
    state_mgr._store = store

    from tests.conftest import MockLLMClient
    listener = ListenerModule.__new__(ListenerModule)
    listener._state = state_mgr
    listener._llm = MockLLMClient(responses={})
    return listener


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_process_submission_stores_response(tmp_path, sample_project_state):
    """Submission is stored in project state."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    listener = _make_listener_with_store(store)
    submission = _make_submission(project_id, pain_score=8, answer="Too much Sunday planning")

    listener.process_submission(submission)

    reloaded = store.load(project_id)
    assert len(reloaded.submissions) == 1
    assert reloaded.submissions[0].pain_score == 8
    assert reloaded.submissions[0].open_ended_answer == "Too much Sunday planning"


def test_generate_weekly_report_returns_report(tmp_path, sample_project_state):
    """Mock LLM, verify WeeklyReport returned."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    # Add a submission so the report has data
    sample_project_state.submissions.append(
        _make_submission(sample_project_state.project_id, pain_score=7, answer="Overwhelmed")
    )
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    listener = _make_listener_with_store(store)
    listener._llm._raw_complete = make_sequence(
        EXTRACT_INSIGHTS_RESPONSE,
        REPORT_TEXT_RESPONSE,
    )

    with patch("auto_validator.integrations.sendgrid.SendGridIntegration.send_email", return_value=True):
        report = listener.generate_weekly_report(project_id)

    assert isinstance(report, WeeklyReport)
    assert report.project_id == project_id
    assert report.lead_count == 1
    assert report.avg_pain_score == 7.0


def test_weekly_report_extracts_insights(tmp_path, sample_project_state):
    """Verify insight buckets parsed correctly from LLM response."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    sample_project_state.submissions.extend([
        _make_submission(sample_project_state.project_id, pain_score=8, answer="Sunday planning nightmare"),
        _make_submission(sample_project_state.project_id, pain_score=9, answer="No work-life balance"),
    ])
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    listener = _make_listener_with_store(store)
    listener._llm._raw_complete = make_sequence(
        EXTRACT_INSIGHTS_RESPONSE,
        REPORT_TEXT_RESPONSE,
    )

    with patch("auto_validator.integrations.sendgrid.SendGridIntegration.send_email", return_value=True):
        report = listener.generate_weekly_report(project_id)

    assert len(report.buckets) == 2
    assert report.buckets[0].label == "Time overload"
    assert report.buckets[0].answer_count == 15
    assert report.buckets[0].percentage == 60.0

    assert len(report.pivot_signals) == 1
    assert report.pivot_signals[0].signal_type == PivotSignalType.PRICE
    assert report.pivot_signals[0].confidence == 0.3


def test_process_multiple_submissions(tmp_path, sample_project_state):
    """Multiple submissions all stored."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    listener = _make_listener_with_store(store)

    submissions = [
        QuizSubmission(
            project_id=project_id,
            respondent_id=f"resp-{i:03d}",
            answers={"q1": "Yes"},
            open_ended_answer=f"Answer number {i}",
            pain_score=i,
            qualified=True,
            submitted_at="2026-03-27T10:00:00+00:00",
        )
        for i in range(1, 6)
    ]

    for sub in submissions:
        listener.process_submission(sub)

    reloaded = store.load(project_id)
    assert len(reloaded.submissions) == 5
    respondent_ids = {s.respondent_id for s in reloaded.submissions}
    assert respondent_ids == {f"resp-{i:03d}" for i in range(1, 6)}


def test_generate_weekly_report_no_submissions(tmp_path, sample_project_state):
    """When there are no submissions, report returns zero counts and no buckets."""
    store = JsonFileStore(data_dir=tmp_path / "projects")
    # Ensure no submissions in state
    sample_project_state.submissions.clear()
    store.save(sample_project_state)
    project_id = sample_project_state.project_id

    listener = _make_listener_with_store(store)

    report = listener.generate_weekly_report(project_id)

    assert isinstance(report, WeeklyReport)
    assert report.lead_count == 0
    assert report.buckets == []
    assert report.pivot_signals == []

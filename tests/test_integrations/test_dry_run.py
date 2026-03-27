"""Confirm dry_run=True never calls external APIs."""
from unittest.mock import patch, MagicMock

import pytest

from auto_validator.models.closer import Email
from auto_validator.models.creative import QuizQuestion, QuestionType


@pytest.fixture(autouse=True)
def enable_dry_run():
    from auto_validator import config
    original = config.settings.dry_run
    config.settings.dry_run = True
    yield
    config.settings.dry_run = original


def test_google_docs_dry_run_returns_mock_url():
    from auto_validator.integrations.google_docs import GoogleDocsIntegration
    gdocs = GoogleDocsIntegration()
    url = gdocs.create_doc("Test Doc", "Some content")
    assert "[DRY RUN]" in url


def test_tally_dry_run_returns_mock_id(tmp_path):
    from auto_validator import config
    config.settings.output_dir = tmp_path
    from auto_validator.integrations.tally import TallyIntegration
    questions = [
        QuizQuestion(
            question_id="q1",
            question_text="Are you a teacher?",
            question_type=QuestionType.QUALIFICATION,
            options=["Yes", "No"],
        )
    ]
    tally = TallyIntegration()
    form_id = tally.create_quiz(questions, "Test Quiz")
    assert "[DRY RUN]" in form_id


def test_sendgrid_dry_run_does_not_call_api():
    from auto_validator.integrations.sendgrid import SendGridIntegration
    sg = SendGridIntegration()
    email = Email(
        subject="Test",
        preview_text="Preview",
        body_html="<p>Hello</p>",
        body_text="Hello",
    )
    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        result = sg.send_email("test@example.com", email)
        mock_sg.assert_not_called()
    assert result is True


def test_dalle_dry_run_returns_placeholder():
    from auto_validator import config
    config.settings.dalle_enabled = True
    from auto_validator.integrations.dalle import DalleIntegration
    dalle = DalleIntegration()
    url = dalle.generate_image("A teacher at a desk", project_id="test-project")
    assert "[DRY RUN]" in url
    config.settings.dalle_enabled = False

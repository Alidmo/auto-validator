"""Tests for CreativeModule (Module B)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from auto_validator.models.creative import (
    AdHook,
    CreativeOutput,
    LandingPageCopy,
    QuestionType,
    QuizQuestion,
)
from auto_validator.modules.creative import CreativeModule


# ── Canned LLM response data ────────────────────────────────────────────────

AD_HOOKS_RESPONSE = {
    "ad_hooks": [
        {
            "variation_number": 1,
            "hook_text": "Stop spending your Sundays planning. Finally, a system built for K teachers.",
            "angle_type": "direct_benefit",
            "visual_prompt": "A smiling teacher leaving school at 3pm",
        },
        {
            "variation_number": 2,
            "hook_text": "Kindergarten teachers: reclaim your weekends in 7 days or less.",
            "angle_type": "direct_benefit",
            "visual_prompt": "A teacher relaxing at home with a coffee",
        },
    ]
}

VISUAL_PROMPTS_RESPONSE = {
    "ad_hooks": [
        {
            "variation_number": 1,
            "hook_text": "Stop spending your Sundays planning. Finally, a system built for K teachers.",
            "angle_type": "direct_benefit",
            "visual_prompt": "Bright classroom, teacher smiling, clock showing 3pm",
        },
        {
            "variation_number": 2,
            "hook_text": "Kindergarten teachers: reclaim your weekends in 7 days or less.",
            "angle_type": "direct_benefit",
            "visual_prompt": "Teacher at a cafe table, weekend vibes",
        },
    ]
}

LANDING_PAGE_RESPONSE = {
    "above_fold_headline": "Lesson planning in 30 minutes a day",
    "above_fold_subheadline": "Built for kindergarten teachers who want their evenings back.",
    "problem_section": "You spend every Sunday planning the week ahead...",
    "desired_outcome_section": "Imagine leaving school at 3pm feeling done.",
    "social_proof_placeholder": "Join 1,200+ teachers who reclaimed their time.",
    "cta_text": "Get Free Access",
    "cta_subtext": "No credit card required.",
}

QUIZ_RESPONSE = {
    "quiz_questions": [
        {
            "question_id": "q1",
            "question_text": "Are you currently a kindergarten teacher?",
            "question_type": "qualification",
            "options": ["Yes", "No"],
            "required": True,
        },
        {
            "question_id": "q2",
            "question_text": "How many hours per week do you spend on lesson planning?",
            "question_type": "pain_scale",
            "options": [],
            "required": True,
        },
        {
            "question_id": "q3",
            "question_text": "Describe your biggest planning challenge.",
            "question_type": "open_ended",
            "options": [],
            "required": False,
        },
    ]
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


def _make_module_with_seq(*responses) -> CreativeModule:
    """Instantiate CreativeModule with a mocked LLM returning given responses."""
    module = CreativeModule.__new__(CreativeModule)
    from tests.conftest import MockLLMClient
    module._llm = MockLLMClient(responses={})
    module._llm._raw_complete = make_sequence(*responses)
    return module


# ── Tests ────────────────────────────────────────────────────────────────────

def test_creative_generates_ad_hooks(sample_strategist_output, tmp_path):
    """mock LLM returns valid AdHooks list."""
    module = CreativeModule.__new__(CreativeModule)
    from tests.conftest import MockLLMClient
    module._llm = MockLLMClient(responses={})
    module._llm._raw_complete = make_sequence(AD_HOOKS_RESPONSE)

    hooks = module._generate_ad_hooks(
        idea=sample_strategist_output.refined_idea,
        angle=sample_strategist_output.chosen_angle,
        avatar=sample_strategist_output.avatar,
    )

    assert isinstance(hooks, list)
    assert len(hooks) == 2
    assert all(isinstance(h, AdHook) for h in hooks)
    assert hooks[0].variation_number == 1
    assert "Sunday" in hooks[0].hook_text


def test_creative_generates_landing_page(sample_strategist_output):
    """mock LLM returns valid LandingPageCopy."""
    module = CreativeModule.__new__(CreativeModule)
    from tests.conftest import MockLLMClient
    module._llm = MockLLMClient(responses={})
    module._llm._raw_complete = make_sequence(LANDING_PAGE_RESPONSE)

    lp = module._generate_landing_page(
        idea=sample_strategist_output.refined_idea,
        angle=sample_strategist_output.chosen_angle,
        avatar=sample_strategist_output.avatar,
    )

    assert isinstance(lp, LandingPageCopy)
    assert "30 minutes" in lp.above_fold_headline
    assert lp.cta_text == "Get Free Access"


def test_creative_generates_quiz(sample_strategist_output):
    """mock LLM returns valid quiz questions."""
    module = CreativeModule.__new__(CreativeModule)
    from tests.conftest import MockLLMClient
    module._llm = MockLLMClient(responses={})
    module._llm._raw_complete = make_sequence(QUIZ_RESPONSE)

    questions = module._generate_quiz(
        idea=sample_strategist_output.refined_idea,
        avatar=sample_strategist_output.avatar,
    )

    assert isinstance(questions, list)
    assert len(questions) == 3
    assert all(isinstance(q, QuizQuestion) for q in questions)
    types = {q.question_type for q in questions}
    assert QuestionType.QUALIFICATION in types
    assert QuestionType.OPEN_ENDED in types


def test_creative_dry_run_no_real_api_calls(sample_strategist_output, tmp_path):
    """Verify integrations don't call external APIs when DRY_RUN=true."""
    from auto_validator import config
    original_dry_run = config.settings.dry_run
    original_output_dir = config.settings.output_dir
    config.settings.dry_run = True
    config.settings.output_dir = tmp_path

    try:
        module = _make_module_with_seq(
            AD_HOOKS_RESPONSE,
            VISUAL_PROMPTS_RESPONSE,
            LANDING_PAGE_RESPONSE,
            QUIZ_RESPONSE,
        )

        with patch("auto_validator.integrations.google_docs.GoogleDocsIntegration.create_doc",
                   return_value="[DRY RUN] https://docs.google.com/mock") as mock_gdocs, \
             patch("auto_validator.integrations.tally.TallyIntegration.create_quiz",
                   return_value="[DRY RUN] tally-form-mock-id") as mock_tally, \
             patch("auto_validator.utils.markdown_export.export_to_markdown",
                   return_value="# Mock markdown"):

            output = module.run(sample_strategist_output)

        # Google Docs and Tally integrations were invoked but in dry-run mode
        mock_gdocs.assert_called_once()
        mock_tally.assert_called_once()
        # No real HTTP calls made — mocks confirm it
    finally:
        config.settings.dry_run = original_dry_run
        config.settings.output_dir = original_output_dir


def test_creative_full_run(sample_strategist_output, tmp_path):
    """End-to-end with mocked LLM returns CreativeOutput."""
    from auto_validator import config
    original_dry_run = config.settings.dry_run
    original_output_dir = config.settings.output_dir
    config.settings.dry_run = True
    config.settings.output_dir = tmp_path

    try:
        module = _make_module_with_seq(
            AD_HOOKS_RESPONSE,
            VISUAL_PROMPTS_RESPONSE,
            LANDING_PAGE_RESPONSE,
            QUIZ_RESPONSE,
        )

        with patch("auto_validator.utils.markdown_export.export_to_markdown",
                   return_value="# Mock markdown content"):
            output = module.run(sample_strategist_output)

        assert isinstance(output, CreativeOutput)
        assert len(output.ad_hooks) > 0
        assert isinstance(output.landing_page, LandingPageCopy)
        assert len(output.quiz_questions) > 0
        assert output.tally_quiz_id is not None
    finally:
        config.settings.dry_run = original_dry_run
        config.settings.output_dir = original_output_dir

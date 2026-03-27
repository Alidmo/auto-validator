import json
import pytest
from unittest.mock import patch

from auto_validator.models.strategist import Angle, CustomerAvatar, TimelessEquation
from auto_validator.modules.strategist import StrategistModule


ANGLE = {
    "angles": [{
        "type": "direct_benefit",
        "headline": "Save 5 hours a week on lesson planning",
        "description": "Direct outcome focus",
        "target_audience": "Overwhelmed kindergarten teachers",
        "rationale": "Strong ROI angle",
    }]
}

AVATAR = {
    "name": "Sarah",
    "age_range": "26-32",
    "occupation": "Kindergarten teacher",
    "pain_points": ["Too much planning time"],
    "failed_solutions": ["Generic apps"],
    "desired_outcome": "Leave at 3pm",
    "biggest_fear": "Burnout",
    "psychographics": "Passionate but exhausted",
    "daily_frustrations": ["Email overload"],
    "buying_triggers": ["Peer recommendation"],
}

EQUATION_LOW_PAIN = {
    "people_score": 6, "people_analysis": "ok",
    "problem_score": 6, "problem_analysis": "ok",
    "solution_score": 6, "solution_analysis": "ok",
    "message_score": 6, "message_analysis": "ok",
    "pain_score": 3,  # Low — triggers refinement loop
    "overall_valid": False,
    "validation_notes": "Niche too broad",
    "refinement_suggestion": "Focus on first-year teachers only",
}

EQUATION_HIGH_PAIN = {**EQUATION_LOW_PAIN, "pain_score": 8, "overall_valid": True, "refinement_suggestion": None}

REFINE_RESPONSE = {
    "refined_idea": "A lesson planner for first-year kindergarten teachers in Title I schools",
    "what_changed": "Narrowed to first-year teachers with highest pain",
    "expected_pain_score": 8,
}


def make_sequence(*responses):
    """Create a mock that returns responses in sequence."""
    responses = list(responses)
    call_count = [0]

    def side_effect(system, user, temperature):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return json.dumps(responses[idx])

    return side_effect


def test_strategist_succeeds_on_first_attempt():
    """When pain score is high enough, no refinement loop runs."""
    seq = make_sequence(ANGLE, AVATAR, EQUATION_HIGH_PAIN)
    module = StrategistModule(auto_select_angle=True)

    with patch.object(module._llm, "_raw_complete", side_effect=seq):
        result = module.run("A productivity app for kindergarten teachers")

    assert result.equation.pain_score == 8
    assert result.refinement_iterations == 0
    assert result.chosen_angle.type == "direct_benefit"


def test_strategist_refines_on_low_pain():
    """When pain score is low, it refines the niche and retries."""
    # Sequence: angles, avatar, low-pain equation, refine_niche, new angles, new avatar, high-pain equation
    seq = make_sequence(
        ANGLE, AVATAR, EQUATION_LOW_PAIN,  # first attempt — pain too low
        REFINE_RESPONSE,                    # refine
        ANGLE, AVATAR, EQUATION_HIGH_PAIN,  # second attempt — passes
    )
    module = StrategistModule(auto_select_angle=True)

    with patch.object(module._llm, "_raw_complete", side_effect=seq):
        result = module.run("A productivity app for teachers")

    assert result.equation.pain_score == 8
    assert result.refinement_iterations == 1
    assert result.refined_idea == REFINE_RESPONSE["refined_idea"]

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auto_validator.llm.base import LLMClient
from auto_validator.models.project import ProjectState
from auto_validator.models.strategist import Angle, CustomerAvatar, StrategistOutput, TimelessEquation
from auto_validator.state.json_store import JsonFileStore


SAMPLE_ANGLE = Angle(
    type="direct_benefit",
    headline="Finally get your classroom under control in 30 minutes a day",
    description="Targets teachers who are overwhelmed by admin work.",
    target_audience="First-year kindergarten teachers",
    rationale="Strong pain, clear outcome.",
)

SAMPLE_AVATAR = CustomerAvatar(
    name="Sarah",
    age_range="26-32",
    occupation="Kindergarten teacher",
    pain_points=["Spends 3 hours on lesson planning every Sunday", "No work-life balance"],
    failed_solutions=["Generic teacher planner apps", "Pinterest boards"],
    desired_outcome="Leave school at 3pm every day without guilt",
    biggest_fear="Burning out before end of year",
    psychographics="Passionate about teaching but exhausted by paperwork.",
    daily_frustrations=["Email overload", "Printing broken lesson materials"],
    buying_triggers=["Free trial", "Testimonial from a fellow teacher"],
)

SAMPLE_EQUATION = TimelessEquation(
    people_score=8,
    people_analysis="Well-defined audience.",
    problem_score=9,
    problem_analysis="Acute daily pain.",
    solution_score=7,
    solution_analysis="Differentiated from generic planners.",
    message_score=8,
    message_analysis="Speaks teacher language.",
    pain_score=8,
    overall_valid=True,
    validation_notes="Strong hypothesis.",
    refinement_suggestion=None,
)


@pytest.fixture
def sample_strategist_output() -> StrategistOutput:
    return StrategistOutput(
        raw_idea="A productivity app for kindergarten teachers",
        refined_idea="A lesson planning app for first-year kindergarten teachers",
        all_angles=[SAMPLE_ANGLE],
        chosen_angle=SAMPLE_ANGLE,
        avatar=SAMPLE_AVATAR,
        equation=SAMPLE_EQUATION,
    )


@pytest.fixture
def sample_project_state(sample_strategist_output) -> ProjectState:
    return ProjectState(
        idea="A productivity app for kindergarten teachers",
        strategist_output=sample_strategist_output,
    )


@pytest.fixture
def temp_json_store(tmp_path: Path) -> JsonFileStore:
    return JsonFileStore(data_dir=tmp_path / "projects")


class MockLLMClient(LLMClient):
    """Returns deterministic canned responses for testing."""

    def __init__(self, responses: dict[str, dict]):
        self._responses = responses  # map of model_name -> dict data

    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        # Return first available response as JSON
        for data in self._responses.values():
            return json.dumps(data)
        return "{}"


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    return MockLLMClient(responses={
        "Angle": {"angles": [SAMPLE_ANGLE.model_dump()]},
        "CustomerAvatar": SAMPLE_AVATAR.model_dump(),
        "TimelessEquation": SAMPLE_EQUATION.model_dump(),
    })

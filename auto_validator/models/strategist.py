from typing import Optional
from pydantic import BaseModel, Field


class Angle(BaseModel):
    type: str = Field(description="'story', 'direct_benefit', or 'controversy'")
    headline: str
    description: str
    target_audience: str
    rationale: str


class CustomerAvatar(BaseModel):
    name: str
    age_range: str
    occupation: str
    pain_points: list[str]
    failed_solutions: list[str]
    desired_outcome: str
    biggest_fear: str
    psychographics: str
    daily_frustrations: list[str]
    buying_triggers: list[str]


class TimelessEquation(BaseModel):
    people_score: int = Field(ge=1, le=10)
    people_analysis: str
    problem_score: int = Field(ge=1, le=10)
    problem_analysis: str
    solution_score: int = Field(ge=1, le=10)
    solution_analysis: str
    message_score: int = Field(ge=1, le=10)
    message_analysis: str
    pain_score: int = Field(ge=1, le=10, description="Composite pain intensity score")
    overall_valid: bool
    validation_notes: str
    refinement_suggestion: Optional[str] = None


class StrategistOutput(BaseModel):
    raw_idea: str
    refined_idea: str
    all_angles: list[Angle]
    chosen_angle: Angle
    avatar: CustomerAvatar
    equation: TimelessEquation
    refinement_iterations: int = 0

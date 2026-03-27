from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PivotSignalType(str, Enum):
    PRICE = "price"
    PROBLEM_MISMATCH = "problem_mismatch"
    NEW_ANGLE = "new_angle"
    WRONG_AUDIENCE = "wrong_audience"


class QuizSubmission(BaseModel):
    project_id: str
    respondent_id: str = ""
    answers: dict[str, Any]
    open_ended_answer: str = ""
    pain_score: Optional[int] = None
    qualified: Optional[bool] = None
    submitted_at: str = ""


class InsightBucket(BaseModel):
    label: str
    answer_count: int
    percentage: float
    representative_quotes: list[str]
    sentiment: str = ""


class PivotSignal(BaseModel):
    signal_type: PivotSignalType
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    recommended_action: str


class WeeklyReport(BaseModel):
    project_id: str
    lead_count: int
    avg_pain_score: float
    top_pain_point: str
    buckets: list[InsightBucket]
    pivot_signals: list[PivotSignal]
    recommendation_text: str
    period_start: str = ""
    period_end: str = ""


class ListenerConfig(BaseModel):
    webhook_secret: str = ""
    tally_form_id: str = ""
    typeform_form_id: str = ""

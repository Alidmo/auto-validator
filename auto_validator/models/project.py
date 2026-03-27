import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from auto_validator.models.closer import CloserOutput
from auto_validator.models.creative import CreativeOutput
from auto_validator.models.listener import ListenerConfig, QuizSubmission, WeeklyReport
from auto_validator.models.metrics import ProjectMetrics
from auto_validator.models.strategist import StrategistOutput


class ProjectStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    A_COMPLETE = "A_COMPLETE"
    B_COMPLETE = "B_COMPLETE"
    LIVE = "LIVE"
    VALIDATED = "VALIDATED"
    REFINEMENT = "REFINEMENT"


class ProjectState(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idea: str
    status: ProjectStatus = ProjectStatus.INITIALIZED
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    strategist_output: Optional[StrategistOutput] = None
    creative_output: Optional[CreativeOutput] = None
    listener_config: Optional[ListenerConfig] = None
    closer_output: Optional[CloserOutput] = None
    metrics: Optional[ProjectMetrics] = None

    submissions: list[QuizSubmission] = []
    weekly_reports: list[WeeklyReport] = []

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

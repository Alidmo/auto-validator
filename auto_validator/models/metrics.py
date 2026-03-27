from enum import Enum
from pydantic import BaseModel, computed_field


class DropOffLocation(str, Enum):
    LANDING_PAGE = "landing_page"
    QUIZ = "quiz"
    NONE = "none"


class ProjectMetrics(BaseModel):
    clicks: int = 0
    leads: int = 0
    drop_off_location: DropOffLocation = DropOffLocation.NONE
    status_tag: str = "Monitoring"
    scaling_ads_drafted: bool = False
    refinement_triggered: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cvr(self) -> float:
        if self.clicks == 0:
            return 0.0
        return self.leads / self.clicks

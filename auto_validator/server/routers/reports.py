from fastapi import APIRouter, Depends, HTTPException

from auto_validator.exceptions import ProjectNotFoundError
from auto_validator.models.listener import WeeklyReport
from auto_validator.models.metrics import ProjectMetrics
from auto_validator.modules.listener import ListenerModule
from auto_validator.server.dependencies import get_listener_module, get_state_manager
from auto_validator.state.manager import StateManager

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{project_id}/weekly", response_model=WeeklyReport)
def get_weekly_report(
    project_id: str,
    listener: ListenerModule = Depends(get_listener_module),
) -> WeeklyReport:
    """Generate and return a weekly insight report on demand."""
    try:
        return listener.generate_weekly_report(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/status")
def get_status(
    project_id: str,
    state_mgr: StateManager = Depends(get_state_manager),
) -> dict:
    """Return current project status and metrics."""
    try:
        state = state_mgr.load(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": state.project_id,
        "status": state.status.value,
        "idea": state.idea,
        "submission_count": len(state.submissions),
        "metrics": state.metrics.model_dump() if state.metrics else None,
    }

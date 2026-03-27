import json
from pathlib import Path

from auto_validator.config import settings
from auto_validator.exceptions import ProjectNotFoundError
from auto_validator.models.project import ProjectState


class JsonFileStore:
    """Filesystem-based project store. One JSON file per project."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or settings.data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        return self._dir / f"{project_id}.json"

    def save(self, state: ProjectState) -> None:
        state.touch()
        self._path(state.project_id).write_text(
            state.model_dump_json(indent=2), encoding="utf-8"
        )

    def load(self, project_id: str) -> ProjectState:
        path = self._path(project_id)
        if not path.exists():
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return ProjectState.model_validate_json(path.read_text(encoding="utf-8"))

    def list_all(self) -> list[ProjectState]:
        projects = []
        for path in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                projects.append(ProjectState.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                pass  # Skip corrupt files
        return projects

    def delete(self, project_id: str) -> None:
        path = self._path(project_id)
        if not path.exists():
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        path.unlink()

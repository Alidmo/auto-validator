from auto_validator.config import settings
from auto_validator.exceptions import ProjectNotFoundError
from auto_validator.models.project import ProjectState
from auto_validator.state.json_store import JsonFileStore


class StateManager:
    """
    Single interface for all project persistence.
    Delegates to Supabase when configured, otherwise JsonFileStore.
    """

    def __init__(self) -> None:
        if settings.supabase_url and settings.supabase_key:
            from auto_validator.integrations.supabase_store import SupabaseStore
            self._store = SupabaseStore()
        else:
            self._store = JsonFileStore()

    def create_project(self, idea: str) -> ProjectState:
        state = ProjectState(idea=idea)
        self._store.save(state)
        return state

    def save(self, state: ProjectState) -> None:
        self._store.save(state)

    def load(self, project_id: str) -> ProjectState:
        return self._store.load(project_id)

    def list_all(self) -> list[ProjectState]:
        return self._store.list_all()

    def delete(self, project_id: str) -> None:
        self._store.delete(project_id)

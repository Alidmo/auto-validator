from auto_validator.config import settings
from auto_validator.exceptions import ProjectNotFoundError, IntegrationError
from auto_validator.models.project import ProjectState


class SupabaseStore:
    """Supabase-backed project store. Used when SUPABASE_URL and SUPABASE_KEY are set."""

    TABLE = "projects"

    def __init__(self) -> None:
        try:
            from supabase import create_client
            self._client = create_client(settings.supabase_url, settings.supabase_key)
        except Exception as exc:
            raise IntegrationError(f"Supabase connection failed: {exc}") from exc

    def save(self, state: ProjectState) -> None:
        state.touch()
        data = state.model_dump(mode="json")
        self._client.table(self.TABLE).upsert(data).execute()

    def load(self, project_id: str) -> ProjectState:
        result = (
            self._client.table(self.TABLE)
            .select("*")
            .eq("project_id", project_id)
            .single()
            .execute()
        )
        if not result.data:
            raise ProjectNotFoundError(f"Project not found: {project_id}")
        return ProjectState.model_validate(result.data)

    def list_all(self) -> list[ProjectState]:
        result = (
            self._client.table(self.TABLE)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [ProjectState.model_validate(row) for row in (result.data or [])]

    def delete(self, project_id: str) -> None:
        self._client.table(self.TABLE).delete().eq("project_id", project_id).execute()

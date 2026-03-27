import json

from rich.console import Console

from auto_validator.config import settings

console = Console()


class BaseIntegration:
    """All integrations inherit from this. Provides dry_run flag and logging helper."""

    @property
    def dry_run(self) -> bool:
        return settings.dry_run

    def _log_dry_run(self, action: str, payload: dict) -> None:
        console.print(f"[dim][DRY RUN] {action}[/dim]")
        console.print(f"[dim]{json.dumps(payload, indent=2, default=str)[:500]}[/dim]")

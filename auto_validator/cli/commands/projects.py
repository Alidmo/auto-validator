import click
from rich.console import Console
from rich.table import Table
from rich import box

from auto_validator.state.manager import StateManager
from auto_validator.utils.output_formatter import print_project_summary

console = Console()


@click.group("projects")
def projects_group() -> None:
    """List and manage validation projects."""


@projects_group.command("list")
def list_projects() -> None:
    """List all projects."""
    projects = StateManager().list_all()
    if not projects:
        console.print("[yellow]No projects found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, title=f"{len(projects)} Projects")
    table.add_column("ID (short)", width=10)
    table.add_column("Status", width=14)
    table.add_column("Idea")
    table.add_column("Created", width=12)
    table.add_column("CVR", width=8, justify="center")

    for p in projects:
        cvr = f"{p.metrics.cvr:.1%}" if p.metrics else "—"
        table.add_row(
            p.project_id[:8],
            p.status.value,
            p.idea[:55],
            p.created_at[:10],
            cvr,
        )
    console.print(table)


@projects_group.command("show")
@click.option("--project-id", required=True)
def show_project(project_id: str) -> None:
    """Show full project state."""
    state = StateManager().load(project_id)
    print_project_summary(state)


@projects_group.command("delete")
@click.option("--project-id", required=True)
@click.confirmation_option(prompt="Are you sure you want to delete this project?")
def delete_project(project_id: str) -> None:
    """Delete a project permanently."""
    StateManager().delete(project_id)
    console.print(f"[green]Project {project_id[:8]} deleted.[/green]")

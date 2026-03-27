import click
from rich.console import Console

from auto_validator.modules.closer import CloserModule
from auto_validator.modules.creative import CreativeModule
from auto_validator.modules.strategist import StrategistModule
from auto_validator.models.project import ProjectStatus
from auto_validator.state.manager import StateManager
from auto_validator.utils.output_formatter import print_banner, print_creative_output, print_strategist_output
from auto_validator.utils.markdown_export import export_to_markdown
from auto_validator.config import settings

console = Console()


@click.command("run")
@click.option("--idea", "-i", required=True, help="Your one-sentence business idea")
@click.option("--auto", is_flag=True, default=False, help="Auto-select first angle (non-interactive)")
def run_command(idea: str, auto: bool) -> None:
    """Run the full validation pipeline: Strategist → Creative Studio → Closer."""
    print_banner()
    console.print(f"\n[bold]Validating:[/bold] {idea}\n")

    state_mgr = StateManager()
    state = state_mgr.create_project(idea)
    console.print(f"[dim]Project ID: {state.project_id}[/dim]\n")

    # ── Module A ───────────────────────────────────────────────────────────────
    strategist = StrategistModule(auto_select_angle=auto)
    try:
        strategist_output = strategist.run(idea)
    except Exception as exc:
        console.print(f"[red]Strategist failed: {exc}[/red]")
        raise SystemExit(1)

    state.strategist_output = strategist_output
    state.status = ProjectStatus.A_COMPLETE
    state_mgr.save(state)
    print_strategist_output(strategist_output)

    # ── Module B ───────────────────────────────────────────────────────────────
    creative = CreativeModule()
    try:
        creative_output = creative.run(strategist_output)
    except Exception as exc:
        console.print(f"[red]Creative Studio failed: {exc}[/red]")
        raise SystemExit(1)

    state.creative_output = creative_output
    state.status = ProjectStatus.B_COMPLETE
    state_mgr.save(state)
    print_creative_output(creative_output)

    # ── Module D (thank-you email setup) ──────────────────────────────────────
    closer = CloserModule(state_manager=state_mgr)
    try:
        thank_you = closer.generate_thank_you(state.project_id)
        console.print(f"\n[bold cyan]── Module D: Closer ─────────────────────[/bold cyan]")
        console.print(f"[green]Thank-you email ready:[/green] {thank_you.subject}")
    except Exception as exc:
        console.print(f"[yellow]Closer setup skipped: {exc}[/yellow]")

    # ── Final output ──────────────────────────────────────────────────────────
    state = state_mgr.load(state.project_id)
    export_path = settings.output_dir / "exports" / f"{state.project_id[:8]}.md"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(export_to_markdown(state), encoding="utf-8")

    console.print(f"\n[bold green]✓ Validation complete![/bold green]")
    console.print(f"  Project ID : [cyan]{state.project_id}[/cyan]")
    console.print(f"  Report     : {export_path}")
    console.print(f"\n[dim]Next: auto-validator metrics update --project-id {state.project_id} --clicks N --leads N[/dim]")

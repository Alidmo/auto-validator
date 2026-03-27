import click
from rich.console import Console
from rich.panel import Panel

from auto_validator.models.metrics import DropOffLocation, ProjectMetrics
from auto_validator.models.project import ProjectStatus
from auto_validator.modules.creative import CreativeModule
from auto_validator.state.manager import StateManager
from auto_validator.utils.cvr_logic import evaluate_cvr

console = Console()


@click.group("metrics")
def metrics_group() -> None:
    """Track campaign performance and trigger smart CVR logic."""


@metrics_group.command("update")
@click.option("--project-id", required=True)
@click.option("--clicks", type=int, required=True)
@click.option("--leads", type=int, required=True)
@click.option(
    "--drop-off",
    type=click.Choice(["landing_page", "quiz", "none"]),
    default="none",
    help="Where users are dropping off",
)
def update_metrics(project_id: str, clicks: int, leads: int, drop_off: str) -> None:
    """Record click and lead counts, then evaluate CVR thresholds."""
    state_mgr = StateManager()
    state = state_mgr.load(project_id)

    state.metrics = ProjectMetrics(
        clicks=clicks,
        leads=leads,
        drop_off_location=DropOffLocation(drop_off),
    )

    status_tag, actions = evaluate_cvr(state.metrics)
    state.metrics.status_tag = status_tag

    if "draft_scaling_ads" in actions:
        state.status = ProjectStatus.VALIDATED
        state.metrics.scaling_ads_drafted = False
        console.print(f"[bold green]VALIDATED[/bold green] — CVR {state.metrics.cvr:.1%} > threshold!")
        console.print("Generating scaling ads...")
        if state.creative_output:
            creative = CreativeModule()
            scaling_ads = creative.generate_scaling_ads(
                state.creative_output.ad_hooks, state.idea
            )
            state.creative_output.ad_hooks.extend(scaling_ads)
            state.metrics.scaling_ads_drafted = True
            console.print(f"[green]{len(scaling_ads)} scaling ad variations added.[/green]")

    elif "rewrite_headline" in actions:
        state.status = ProjectStatus.REFINEMENT
        state.metrics.refinement_triggered = True
        console.print(f"[yellow]REFINEMENT[/yellow] — CVR {state.metrics.cvr:.1%} < threshold. Drop-off: landing page.")
        console.print("[yellow]Recommendation: Rewrite the landing page headline.[/yellow]")
        console.print(f"[dim]Run: auto-validator strategist analyze --idea \"{state.idea}\"[/dim]")

    elif "simplify_quiz" in actions:
        state.status = ProjectStatus.REFINEMENT
        state.metrics.refinement_triggered = True
        console.print(f"[yellow]REFINEMENT[/yellow] — CVR {state.metrics.cvr:.1%} < threshold. Drop-off: quiz.")
        console.print("[yellow]Recommendation: Simplify the quiz questions.[/yellow]")
    else:
        console.print(f"[blue]MONITORING[/blue] — CVR {state.metrics.cvr:.1%} — within normal range.")

    state_mgr.save(state)
    console.print(f"\n[dim]Status saved: {status_tag}[/dim]")


@metrics_group.command("status")
@click.option("--project-id", required=True)
def show_status(project_id: str) -> None:
    """Show current project metrics and status."""
    state = StateManager().load(project_id)
    if not state.metrics:
        console.print("[yellow]No metrics recorded yet.[/yellow]")
        return

    m = state.metrics
    console.print(Panel(
        f"Clicks: {m.clicks}  |  Leads: {m.leads}  |  CVR: {m.cvr:.1%}\n"
        f"Status: [bold]{m.status_tag}[/bold]\n"
        f"Drop-off: {m.drop_off_location.value}",
        title=f"Metrics — {project_id[:8]}",
        border_style="blue",
    ))

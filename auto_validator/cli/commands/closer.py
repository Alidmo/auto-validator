import click
from rich.console import Console
from rich.panel import Panel

from auto_validator.modules.closer import CloserModule
from auto_validator.state.manager import StateManager

console = Console()


@click.group("closer")
def closer_group() -> None:
    """Generate and send launch email sequences."""


@closer_group.command("thank-you")
@click.option("--project-id", required=True)
@click.option("--email", "email_address", default=None, help="Send to this address (optional)")
def generate_thank_you(project_id: str, email_address: str | None) -> None:
    """Generate (and optionally send) the thank-you email."""
    state_mgr = StateManager()
    closer = CloserModule(state_manager=state_mgr)
    email = closer.generate_thank_you(project_id)

    console.print(Panel(
        f"[bold]Subject:[/bold] {email.subject}\n\n{email.body_text[:500]}",
        title="Thank-You Email",
        border_style="green",
    ))

    if email_address:
        closer.send_thank_you(email_address, project_id)


@closer_group.command("approve-launch")
@click.option("--project-id", required=True)
@click.option("--email", "email_address", default=None, help="Schedule PLF sequence to this address")
def approve_launch(project_id: str, email_address: str | None) -> None:
    """Generate the 4-email PLF sequence and optionally schedule delivery."""
    state_mgr = StateManager()
    closer = CloserModule(state_manager=state_mgr)
    plf = closer.approve_launch(project_id)

    for i, email in enumerate(plf.as_list(), 1):
        labels = ["Curiosity", "Backstory", "Logic", "Open Cart"]
        console.print(Panel(
            f"[bold]Subject:[/bold] {email.subject}\n\n{email.body_text[:300]}...",
            title=f"Email {i} — {labels[i-1]}",
            border_style="cyan",
        ))

    if email_address:
        closer.schedule_plf(email_address, project_id)


@closer_group.command("show-plf")
@click.option("--project-id", required=True)
def show_plf(project_id: str) -> None:
    """Display the stored PLF sequence."""
    state = StateManager().load(project_id)
    if not state.closer_output or not state.closer_output.plf_sequence:
        console.print("[yellow]No PLF sequence generated yet.[/yellow]")
        return

    for i, email in enumerate(state.closer_output.plf_sequence.as_list(), 1):
        labels = ["Curiosity", "Backstory", "Logic", "Open Cart"]
        console.print(Panel(
            f"[bold]Subject:[/bold] {email.subject}\n\n{email.body_text}",
            title=f"Email {i} — {labels[i-1]}",
            border_style="cyan",
        ))

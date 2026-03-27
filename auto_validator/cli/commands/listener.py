import json
import random
import string
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.table import Table
from rich import box

from auto_validator.models.listener import QuizSubmission
from auto_validator.modules.listener import ListenerModule
from auto_validator.state.manager import StateManager

console = Console()


@click.group("listener")
def listener_group() -> None:
    """Manage quiz submissions and generate insight reports."""


@listener_group.command("report")
@click.option("--project-id", required=True)
def generate_report(project_id: str) -> None:
    """Generate a weekly insight report from collected submissions."""
    state_mgr = StateManager()
    listener = ListenerModule(state_manager=state_mgr)
    report = listener.generate_weekly_report(project_id)

    console.print(f"\n[bold cyan]── Weekly Report ─────────────────────────[/bold cyan]")
    console.print(f"Leads: [bold]{report.lead_count}[/bold]  |  Avg Pain Score: [bold]{report.avg_pain_score:.1f}/10[/bold]")
    console.print(f"Top Pain Point: [yellow]{report.top_pain_point}[/yellow]\n")

    if report.buckets:
        table = Table(box=box.ROUNDED, title="Insight Buckets")
        table.add_column("Theme")
        table.add_column("Count", justify="center")
        table.add_column("%", justify="center")
        table.add_column("Sentiment")
        for b in report.buckets:
            table.add_row(b.label, str(b.answer_count), f"{b.percentage:.0f}%", b.sentiment)
        console.print(table)

    if report.pivot_signals:
        console.print("\n[bold yellow]Pivot Signals:[/bold yellow]")
        for s in report.pivot_signals:
            console.print(f"  [{s.signal_type}] {s.description} (confidence: {s.confidence:.0%})")
            console.print(f"  [dim]→ {s.recommended_action}[/dim]")

    console.print(f"\n[bold]Recommendation:[/bold]\n{report.recommendation_text}")


@listener_group.command("simulate")
@click.option("--project-id", required=True)
@click.option("--count", default=20, show_default=True, help="Number of synthetic responses to inject")
def simulate_responses(project_id: str, count: int) -> None:
    """Inject synthetic quiz responses to test the analysis pipeline."""
    state_mgr = StateManager()
    state = state_mgr.load(project_id)

    sample_answers = [
        "I spend hours every week on this and still don't get the results I want.",
        "The biggest problem is I don't know where to start — there's too much conflicting advice.",
        "It's too expensive for what it offers. I need something more affordable.",
        "I've tried three different tools and none of them fit my actual workflow.",
        "I just wish someone would explain it clearly without all the jargon.",
        "Time is my biggest issue. I need something that works fast.",
        "I keep getting distracted and losing momentum. I need accountability.",
        "The price point is too high for me to justify right now.",
        "Nobody seems to understand my specific situation.",
        "I've been burned before by tools that promised too much.",
    ]

    for i in range(count):
        submission = QuizSubmission(
            project_id=project_id,
            respondent_id=f"sim_{i:03d}",
            answers={"q1": "Yes", "q2": str(random.randint(5, 10)), "q3": random.choice(sample_answers)},
            open_ended_answer=random.choice(sample_answers),
            pain_score=random.randint(5, 10),
            qualified=True,
            submitted_at=datetime.now(timezone.utc).isoformat(),
        )
        state.submissions.append(submission)

    state_mgr.save(state)
    console.print(f"[green]{count} synthetic responses added to project {project_id[:8]}.[/green]")
    console.print(f"[dim]Now run: auto-validator listener report --project-id {project_id}[/dim]")

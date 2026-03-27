from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from auto_validator.models.creative import CreativeOutput
from auto_validator.models.project import ProjectState
from auto_validator.models.strategist import StrategistOutput

console = Console()


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Auto-Validator[/bold cyan]\n"
            "[dim]Autonomous Business Idea Validation Agent[/dim]",
            border_style="cyan",
        )
    )


def print_project_summary(state: ProjectState) -> None:
    table = Table(box=box.ROUNDED, show_header=False, border_style="dim")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Project ID", state.project_id)
    table.add_row("Status", f"[green]{state.status.value}[/green]")
    table.add_row("Idea", state.idea)
    table.add_row("Created", state.created_at[:19])
    if state.metrics:
        table.add_row("CVR", f"{state.metrics.cvr:.1%} ({state.metrics.leads}/{state.metrics.clicks})")
    console.print(table)


def print_strategist_output(output: StrategistOutput) -> None:
    console.print("\n[bold cyan]── Module A: Strategist ──────────────────[/bold cyan]")

    console.print(Panel(
        f"[bold]{output.chosen_angle.type.upper()}[/bold]: {output.chosen_angle.headline}\n\n"
        f"{output.chosen_angle.description}\n\n"
        f"[dim]Target: {output.chosen_angle.target_audience}[/dim]",
        title="Chosen Angle",
        border_style="blue",
    ))

    avatar = output.avatar
    avatar_lines = [
        f"[bold]{avatar.name}[/bold], {avatar.age_range}, {avatar.occupation}",
        f"\n[yellow]Pain Points:[/yellow]",
    ]
    for p in avatar.pain_points:
        avatar_lines.append(f"  • {p}")
    avatar_lines.append(f"\n[green]Desired Outcome:[/green] {avatar.desired_outcome}")
    console.print(Panel("\n".join(avatar_lines), title="Customer Avatar", border_style="yellow"))

    eq = output.equation
    score_table = Table(box=box.SIMPLE, border_style="dim")
    score_table.add_column("Dimension")
    score_table.add_column("Score", justify="center")
    score_table.add_column("Notes")
    score_table.add_row("People", _score_color(eq.people_score), eq.people_analysis)
    score_table.add_row("Problem", _score_color(eq.problem_score), eq.problem_analysis)
    score_table.add_row("Solution", _score_color(eq.solution_score), eq.solution_analysis)
    score_table.add_row("Message", _score_color(eq.message_score), eq.message_analysis)
    score_table.add_row("[bold]Pain[/bold]", _score_color(eq.pain_score, bold=True), eq.validation_notes)
    console.print(Panel(score_table, title="Timeless Equation Scores", border_style="magenta"))


def print_creative_output(output: CreativeOutput) -> None:
    console.print("\n[bold cyan]── Module B: Creative Studio ─────────────[/bold cyan]")

    hooks_table = Table(box=box.ROUNDED, title="Facebook Ad Hooks", border_style="blue")
    hooks_table.add_column("#", width=3)
    hooks_table.add_column("Hook", ratio=3)
    hooks_table.add_column("Type", width=18)
    for hook in output.ad_hooks:
        hooks_table.add_row(str(hook.variation_number), hook.hook_text, hook.angle_type)
    console.print(hooks_table)

    lp = output.landing_page
    console.print(Panel(
        f"[bold]{lp.above_fold_headline}[/bold]\n"
        f"[italic]{lp.above_fold_subheadline}[/italic]\n\n"
        f"[yellow]Problem:[/yellow]\n{lp.problem_section[:300]}...\n\n"
        f"[green]CTA:[/green] [{lp.cta_text}] — {lp.cta_subtext}",
        title="Landing Page Copy (preview)",
        border_style="green",
    ))

    quiz_table = Table(box=box.ROUNDED, title="Quiz Questions", border_style="yellow")
    quiz_table.add_column("ID", width=4)
    quiz_table.add_column("Type", width=16)
    quiz_table.add_column("Question")
    for q in output.quiz_questions:
        quiz_table.add_row(q.question_id, q.question_type.value, q.question_text)
    console.print(quiz_table)

    if output.google_doc_url:
        console.print(f"[green]Google Doc:[/green] {output.google_doc_url}")
    if output.tally_quiz_id:
        console.print(f"[green]Tally Quiz:[/green] {output.tally_quiz_id}")


def _score_color(score: int, bold: bool = False) -> str:
    color = "red" if score < 5 else ("yellow" if score < 7 else "green")
    text = f"{score}/10"
    return f"[{color}]{('[bold]' if bold else '')}{text}{('[/bold]' if bold else '')}[/{color}]"

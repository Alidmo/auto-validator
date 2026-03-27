import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from auto_validator.llm.factory import get_llm_client
from auto_validator.modules.strategist import StrategistModule
from auto_validator.utils.prompt_loader import load_prompt

console = Console()


@click.command("discover")
@click.option("--market", "-m", required=True, help='Market or country, e.g. "Netherlands"')
@click.option("--niche", "-n", default="", help='Optional focus area, e.g. "housing" or "healthcare"')
@click.option("--count", "-c", default=5, show_default=True, help="Number of ideas to generate")
@click.option("--validate", is_flag=True, default=False,
              help="Run each idea through the Strategist (takes longer but gives pain scores)")
def discover_command(market: str, niche: str, count: int, validate: bool) -> None:
    """Generate and rank app ideas for a specific market."""
    console.print(f"\n[bold cyan]Discovering app opportunities in:[/bold cyan] [bold]{market}[/bold]")
    if niche:
        console.print(f"[dim]Focus: {niche}[/dim]")
    console.print()

    # Step 1: Generate ideas
    console.print("[dim]Asking Gemini to analyze the market...[/dim]\n")
    llm = get_llm_client()
    system, user = load_prompt(
        "discover", "generate_ideas",
        market=market,
        niche=niche,
        context="",
        count=count,
    )
    result = llm.complete_json(system, user)
    ideas = result.get("ideas", [])

    if not ideas:
        console.print("[red]No ideas generated. Try a different market or niche.[/red]")
        return

    # Step 2: Display raw ideas
    _print_ideas_table(ideas, market)

    if not validate:
        console.print(
            "\n[dim]Tip: Add --validate to run each idea through the full Strategist "
            "(pain scoring, avatar, Timeless Equation). Takes ~1 min per idea.[/dim]"
        )
        console.print(
            "\n[dim]To validate a specific idea:[/dim]\n"
            "  auto-validator run --idea \"<idea>\" --auto"
        )
        return

    # Step 3: Validate each idea through Module A
    console.print(f"\n[bold]Validating {len(ideas)} ideas through the Strategist...[/bold]\n")
    results = []
    strategist = StrategistModule(auto_select_angle=True)

    for i, idea_data in enumerate(ideas, 1):
        idea_text = idea_data["idea"]
        console.print(f"[dim]({i}/{len(ideas)}) Validating: {idea_text[:60]}...[/dim]")
        try:
            output = strategist.run(idea_text)
            results.append({
                "idea": idea_text,
                "pain_score": output.equation.pain_score,
                "problem_score": output.equation.problem_score,
                "people_score": output.equation.people_score,
                "angle": output.chosen_angle.headline,
                "avatar": f"{output.avatar.name}, {output.avatar.occupation}",
                "valid": output.equation.overall_valid,
                "why_market": idea_data.get("why_this_market", ""),
            })
        except Exception as exc:
            console.print(f"  [yellow]Skipped: {exc}[/yellow]")
            results.append({
                "idea": idea_text,
                "pain_score": 0,
                "problem_score": 0,
                "people_score": 0,
                "angle": "—",
                "avatar": "—",
                "valid": False,
                "why_market": idea_data.get("why_this_market", ""),
            })

    # Step 4: Ranked results
    results.sort(key=lambda r: r["pain_score"], reverse=True)
    _print_validation_results(results, market)


def _print_ideas_table(ideas: list, market: str) -> None:
    table = Table(
        title=f"App Opportunities — {market}",
        box=box.ROUNDED,
        show_lines=True,
        border_style="cyan",
    )
    table.add_column("#", width=3, justify="center")
    table.add_column("Idea", ratio=3)
    table.add_column("Target Audience", ratio=2)
    table.add_column("Pain", width=4, justify="center")
    table.add_column("Why this market", ratio=2)

    for i, idea in enumerate(ideas, 1):
        pain = idea.get("estimated_pain_level", "?")
        color = "green" if pain >= 8 else ("yellow" if pain >= 6 else "red")
        table.add_row(
            str(i),
            f"[bold]{idea['idea']}[/bold]\n[dim]{idea['problem_it_solves']}[/dim]",
            idea.get("target_audience", ""),
            f"[{color}]{pain}/10[/{color}]",
            idea.get("why_this_market", ""),
        )

    console.print(table)


def _print_validation_results(results: list, market: str) -> None:
    console.print(f"\n[bold cyan]── Ranked Results (by Pain Score) ───────[/bold cyan]\n")

    table = Table(box=box.ROUNDED, border_style="green", show_lines=True)
    table.add_column("Rank", width=5, justify="center")
    table.add_column("Idea", ratio=3)
    table.add_column("Pain", width=6, justify="center")
    table.add_column("Problem", width=8, justify="center")
    table.add_column("Validated", width=9, justify="center")
    table.add_column("Best Angle", ratio=2)

    for rank, r in enumerate(results, 1):
        pain = r["pain_score"]
        color = "green" if pain >= 8 else ("yellow" if pain >= 6 else "red")
        valid_icon = "[green]YES[/green]" if r["valid"] else "[red]NO[/red]"
        table.add_row(
            f"#{rank}",
            r["idea"],
            f"[{color}]{pain}/10[/{color}]",
            f"{r['problem_score']}/10",
            valid_icon,
            r["angle"],
        )

    console.print(table)

    # Winner callout
    winner = results[0]
    if winner["pain_score"] >= 7:
        console.print(Panel(
            f"[bold green]Top Pick:[/bold green] {winner['idea']}\n\n"
            f"Pain Score: [bold]{winner['pain_score']}/10[/bold]  |  "
            f"Validated: {'YES' if winner['valid'] else 'NO'}\n\n"
            f"Best angle: [italic]{winner['angle']}[/italic]\n\n"
            f"[dim]To run the full pipeline on this idea:[/dim]\n"
            f"  auto-validator run --idea \"{winner['idea']}\" --auto",
            border_style="green",
            title="Recommended",
        ))

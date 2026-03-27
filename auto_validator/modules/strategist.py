from rich.console import Console
from rich.prompt import Prompt

from auto_validator.config import settings
from auto_validator.exceptions import ValidationLoopError
from auto_validator.llm.factory import get_llm_client
from auto_validator.models.strategist import (
    Angle,
    CustomerAvatar,
    StrategistOutput,
    TimelessEquation,
)
from auto_validator.utils.prompt_loader import load_prompt

console = Console()


class _AnglesResponse:
    """Thin wrapper for parsing the angles LLM response."""
    from pydantic import BaseModel

    class _Inner(BaseModel):
        angles: list[Angle]

    @classmethod
    def parse(cls, raw: dict) -> list[Angle]:
        return [Angle(**a) for a in raw["angles"]]


class _RefineResponse:
    from pydantic import BaseModel

    class _Inner(BaseModel):
        refined_idea: str
        what_changed: str
        expected_pain_score: int


class StrategistModule:
    """Module A: Hypothesis Engine — angles, avatar, Timeless Equation validation."""

    def __init__(self, auto_select_angle: bool = False) -> None:
        self._llm = get_llm_client()
        self._auto_select = auto_select_angle  # True in non-interactive / test mode

    def run(self, idea: str) -> StrategistOutput:
        console.print(f"\n[bold blue]Strategist:[/bold blue] Analyzing idea...")
        current_idea = idea
        iterations = 0

        for attempt in range(settings.max_refinement_retries + 1):
            # Step 1: Generate angles
            angles = self._generate_angles(current_idea)

            # Step 2: Choose angle
            chosen = self._choose_angle(angles)

            # Step 3: Create avatar
            avatar = self._create_avatar(current_idea, chosen)

            # Step 4: Validate Timeless Equation
            equation = self._validate_equation(current_idea, chosen, avatar)

            if equation.pain_score >= settings.min_pain_score:
                break

            if attempt >= settings.max_refinement_retries:
                raise ValidationLoopError(
                    f"Pain score ({equation.pain_score}/10) still below minimum "
                    f"({settings.min_pain_score}) after {attempt + 1} refinement attempts."
                )

            console.print(
                f"[yellow]Pain score {equation.pain_score}/10 — too low. "
                f"Refining niche (attempt {attempt + 1}/{settings.max_refinement_retries})...[/yellow]"
            )
            current_idea = self._refine_niche(current_idea, equation)
            iterations += 1

        return StrategistOutput(
            raw_idea=idea,
            refined_idea=current_idea,
            all_angles=angles,
            chosen_angle=chosen,
            avatar=avatar,
            equation=equation,
            refinement_iterations=iterations,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_angles(self, idea: str) -> list[Angle]:
        console.print("[dim]  → Generating marketing angles...[/dim]")
        system, user = load_prompt("strategist", "generate_angles", idea=idea)
        result = self._llm.complete_json(system, user)
        return [Angle(**a) for a in result["angles"]]

    def _choose_angle(self, angles: list[Angle]) -> Angle:
        if self._auto_select or not _is_interactive():
            return angles[0]

        console.print("\n[bold]Choose a marketing angle:[/bold]")
        for i, angle in enumerate(angles, 1):
            console.print(f"  [{i}] [cyan]{angle.type.upper()}[/cyan] — {angle.headline}")
            console.print(f"      [dim]{angle.description}[/dim]")

        choice = Prompt.ask("Select angle", choices=[str(i) for i in range(1, len(angles) + 1)], default="1")
        return angles[int(choice) - 1]

    def _create_avatar(self, idea: str, angle: Angle) -> CustomerAvatar:
        console.print("[dim]  → Building customer avatar...[/dim]")
        system, user = load_prompt(
            "strategist", "create_avatar",
            idea=idea,
            angle_type=angle.type,
            angle_headline=angle.headline,
            target_audience=angle.target_audience,
        )
        return self._llm.complete(system, user, CustomerAvatar)

    def _validate_equation(self, idea: str, angle: Angle, avatar: CustomerAvatar) -> TimelessEquation:
        console.print("[dim]  → Validating Timeless Equation...[/dim]")
        system, user = load_prompt(
            "strategist", "validate_equation",
            idea=idea,
            angle_type=angle.type,
            angle_headline=angle.headline,
            avatar_name=avatar.name,
            avatar_age_range=avatar.age_range,
            avatar_occupation=avatar.occupation,
            top_pain_point=avatar.pain_points[0] if avatar.pain_points else "",
            desired_outcome=avatar.desired_outcome,
        )
        return self._llm.complete(system, user, TimelessEquation)

    def _refine_niche(self, idea: str, equation: TimelessEquation) -> str:
        system, user = load_prompt(
            "strategist", "refine_niche",
            idea=idea,
            pain_score=equation.pain_score,
            validation_notes=equation.validation_notes,
            refinement_suggestion=equation.refinement_suggestion or "Make the niche more specific.",
        )
        result = self._llm.complete_json(system, user)
        refined = result["refined_idea"]
        console.print(f"[dim]  → Refined idea: {refined}[/dim]")
        return refined


def _is_interactive() -> bool:
    import sys
    return sys.stdin.isatty()

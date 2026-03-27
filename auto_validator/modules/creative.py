from rich.console import Console

from auto_validator.config import settings
from auto_validator.exceptions import IntegrationError
from auto_validator.llm.factory import get_llm_client
from auto_validator.models.creative import AdHook, CreativeOutput, LandingPageCopy, QuizQuestion
from auto_validator.models.strategist import StrategistOutput
from auto_validator.utils.prompt_loader import load_prompt

console = Console()


class CreativeModule:
    """Module B: Asset Generation — ad hooks, images, landing page, quiz."""

    def __init__(self) -> None:
        self._llm = get_llm_client()

    def run(self, strategist_output: StrategistOutput) -> CreativeOutput:
        console.print(f"\n[bold blue]Creative Studio:[/bold blue] Generating assets...")

        avatar = strategist_output.avatar
        angle = strategist_output.chosen_angle
        idea = strategist_output.refined_idea

        # 1. Ad hooks
        ad_hooks = self._generate_ad_hooks(idea, angle, avatar)

        # 2. Visual prompts
        ad_hooks = self._generate_visual_prompts(idea, avatar, ad_hooks)

        # 3. Landing page
        landing_page = self._generate_landing_page(idea, angle, avatar)

        # 4. Quiz
        quiz_questions = self._generate_quiz(idea, avatar)

        output = CreativeOutput(
            ad_hooks=ad_hooks,
            landing_page=landing_page,
            quiz_questions=quiz_questions,
        )

        # 5. Generate images (optional)
        if settings.dalle_enabled:
            output.generated_image_urls = self._generate_images(
                ad_hooks, strategist_output.raw_idea
            )

        # 6. Push to Google Docs
        output.google_doc_url = self._push_to_google_docs(output, idea)

        # 7. Create Tally quiz
        result = self._create_tally_quiz(quiz_questions, idea)
        output.tally_quiz_id = result
        output.tally_quiz_json = None  # stored to disk by TallyIntegration

        return output

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_ad_hooks(self, idea, angle, avatar) -> list[AdHook]:
        console.print("[dim]  → Writing 5 ad hook variations...[/dim]")
        system, user = load_prompt(
            "creative", "generate_ad_hooks",
            idea=idea,
            angle_type=angle.type,
            angle_headline=angle.headline,
            avatar_name=avatar.name,
            avatar_age_range=avatar.age_range,
            avatar_occupation=avatar.occupation,
            top_pain_point=avatar.pain_points[0] if avatar.pain_points else "",
            desired_outcome=avatar.desired_outcome,
            buying_triggers=avatar.buying_triggers,
        )
        result = self._llm.complete_json(system, user)
        return [AdHook(**h) for h in result["ad_hooks"]]

    def _generate_visual_prompts(self, idea, avatar, hooks: list[AdHook]) -> list[AdHook]:
        console.print("[dim]  → Creating visual prompts...[/dim]")
        hooks_data = [h.model_dump() for h in hooks]
        system, user = load_prompt(
            "creative", "generate_visual_prompts",
            idea=idea,
            avatar_name=avatar.name,
            avatar_age_range=avatar.age_range,
            avatar_occupation=avatar.occupation,
            hooks=hooks_data,
        )
        result = self._llm.complete_json(system, user)
        updated = [AdHook(**h) for h in result["ad_hooks"]]
        # Preserve original hooks if count mismatch
        if len(updated) != len(hooks):
            return hooks
        return updated

    def _generate_landing_page(self, idea, angle, avatar) -> LandingPageCopy:
        console.print("[dim]  → Writing landing page copy...[/dim]")
        system, user = load_prompt(
            "creative", "generate_landing_page",
            idea=idea,
            angle_type=angle.type,
            angle_headline=angle.headline,
            avatar_name=avatar.name,
            avatar_age_range=avatar.age_range,
            avatar_occupation=avatar.occupation,
            top_pain_point=avatar.pain_points[0] if avatar.pain_points else "",
            desired_outcome=avatar.desired_outcome,
            biggest_fear=avatar.biggest_fear,
        )
        return self._llm.complete(system, user, LandingPageCopy)

    def _generate_quiz(self, idea, avatar) -> list[QuizQuestion]:
        console.print("[dim]  → Building quiz architecture...[/dim]")
        system, user = load_prompt(
            "creative", "generate_quiz",
            idea=idea,
            avatar_name=avatar.name,
            avatar_age_range=avatar.age_range,
            avatar_occupation=avatar.occupation,
            pain_points=avatar.pain_points,
        )
        result = self._llm.complete_json(system, user)
        return [QuizQuestion(**q) for q in result["quiz_questions"]]

    def _generate_images(self, hooks: list[AdHook], project_id: str) -> list[str]:
        from auto_validator.integrations.dalle import DalleIntegration
        dalle = DalleIntegration()
        urls = []
        for hook in hooks:
            if not hook.visual_prompt:
                continue
            try:
                url = dalle.generate_image(
                    hook.visual_prompt,
                    project_id=project_id,
                    filename=f"hook_{hook.variation_number}",
                )
                hook.generated_image_url = url
                urls.append(url)
            except IntegrationError as exc:
                console.print(f"[yellow]Image generation skipped: {exc}[/yellow]")
        return urls

    def _push_to_google_docs(self, output: CreativeOutput, idea: str) -> str | None:
        from auto_validator.integrations.google_docs import GoogleDocsIntegration
        from auto_validator.utils.markdown_export import export_to_markdown
        from auto_validator.models.project import ProjectState

        # Build a temporary state just for export
        temp_state = ProjectState(idea=idea, creative_output=output)
        content = export_to_markdown(temp_state)

        try:
            gdocs = GoogleDocsIntegration()
            return gdocs.create_doc(title=f"Auto-Validator: {idea[:50]}", content=content)
        except IntegrationError as exc:
            console.print(f"[yellow]Google Docs skipped: {exc}[/yellow]")
            # Save locally as fallback
            self._save_markdown_locally(content, idea)
            return None

    def _save_markdown_locally(self, content: str, idea: str) -> None:
        export_path = settings.output_dir / "exports" / f"{idea[:30].replace(' ', '_')}.md"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(content, encoding="utf-8")
        console.print(f"[dim]Report saved locally: {export_path}[/dim]")

    def _create_tally_quiz(self, questions: list[QuizQuestion], idea: str) -> str | None:
        from auto_validator.integrations.tally import TallyIntegration
        try:
            tally = TallyIntegration()
            return tally.create_quiz(questions, title=f"Validation Quiz: {idea[:40]}")
        except IntegrationError as exc:
            console.print(f"[yellow]Tally skipped: {exc}[/yellow]")
            return None

    def generate_scaling_ads(self, winning_hooks: list[AdHook], idea: str) -> list[AdHook]:
        """Called by CVR logic when CVR > 20%."""
        console.print("[dim]  → Generating scaling ad variations...[/dim]")
        system, user = load_prompt(
            "creative", "generate_scaling_ads",
            idea=idea,
            winning_hooks=[h.model_dump() for h in winning_hooks],
        )
        result = self._llm.complete_json(system, user)
        return [AdHook(**h) for h in result["ad_hooks"]]

from rich.console import Console

from auto_validator.exceptions import IntegrationError
from auto_validator.llm.factory import get_llm_client
from auto_validator.models.closer import CloserOutput, Email, PLFSequence
from auto_validator.state.manager import StateManager
from auto_validator.utils.prompt_loader import load_prompt

console = Console()


class CloserModule:
    """Module D: Launch Sequence — thank-you email and PLF 4-email sequence."""

    def __init__(self, state_manager: StateManager | None = None) -> None:
        self._llm = get_llm_client()
        self._state = state_manager or StateManager()

    def generate_thank_you(self, project_id: str) -> Email:
        state = self._state.load(project_id)
        if not state.strategist_output:
            raise ValueError("Module A must run before generating emails.")

        console.print("[dim]  → Writing thank-you email...[/dim]")
        s = state.strategist_output
        system, user = load_prompt(
            "closer", "generate_thank_you_email",
            idea=s.refined_idea,
            angle_headline=s.chosen_angle.headline,
            desired_outcome=s.avatar.desired_outcome,
            top_pain_point=s.avatar.pain_points[0] if s.avatar.pain_points else "",
        )
        email = self._llm.complete(system, user, Email)

        # Save to state
        if state.closer_output is None:
            state.closer_output = CloserOutput(thank_you_email=email)
        else:
            state.closer_output.thank_you_email = email
        self._state.save(state)
        return email

    def approve_launch(self, project_id: str) -> PLFSequence:
        """Generate the full 4-email PLF sequence and mark launch as approved."""
        state = self._state.load(project_id)
        if not state.strategist_output:
            raise ValueError("Module A must run before generating a launch sequence.")

        console.print(f"\n[bold blue]Closer:[/bold blue] Generating PLF launch sequence...")
        s = state.strategist_output
        system, user = load_prompt(
            "closer", "generate_plf_sequence",
            idea=s.refined_idea,
            angle_headline=s.chosen_angle.headline,
            avatar_name=s.avatar.name,
            avatar_age_range=s.avatar.age_range,
            avatar_occupation=s.avatar.occupation,
            top_pain_point=s.avatar.pain_points[0] if s.avatar.pain_points else "",
            desired_outcome=s.avatar.desired_outcome,
        )
        plf = self._llm.complete(system, user, PLFSequence)

        if state.closer_output is None:
            # Generate thank-you email if not already done
            thank_you = self.generate_thank_you(project_id)
            state = self._state.load(project_id)  # reload after save
            state.closer_output = CloserOutput(thank_you_email=thank_you, plf_sequence=plf, launch_approved=True)
        else:
            state.closer_output.plf_sequence = plf
            state.closer_output.launch_approved = True

        self._state.save(state)
        return plf

    def send_thank_you(self, email_address: str, project_id: str) -> None:
        """Send the thank-you email to a specific subscriber."""
        state = self._state.load(project_id)
        if not state.closer_output:
            self.generate_thank_you(project_id)
            state = self._state.load(project_id)

        from auto_validator.integrations.sendgrid import SendGridIntegration
        try:
            sg = SendGridIntegration()
            sg.send_email(email_address, state.closer_output.thank_you_email)
            console.print(f"[green]Thank-you email sent to {email_address}[/green]")
        except IntegrationError as exc:
            console.print(f"[yellow]Email not sent: {exc}[/yellow]")

    def schedule_plf(self, email_address: str, project_id: str) -> None:
        """Schedule the full PLF sequence delivery."""
        state = self._state.load(project_id)
        if not state.closer_output or not state.closer_output.plf_sequence:
            raise ValueError("Run approve_launch first to generate the PLF sequence.")

        from auto_validator.integrations.sendgrid import SendGridIntegration
        try:
            sg = SendGridIntegration()
            sg.schedule_sequence(
                to=email_address,
                emails=state.closer_output.plf_sequence.as_list(),
                send_days=[0, 2, 4, 6],
            )
            console.print(f"[green]PLF sequence scheduled for {email_address}[/green]")
        except IntegrationError as exc:
            console.print(f"[yellow]PLF scheduling failed: {exc}[/yellow]")

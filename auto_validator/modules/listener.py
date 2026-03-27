from datetime import datetime, timezone

from rich.console import Console

from auto_validator.exceptions import IntegrationError, ProjectNotFoundError
from auto_validator.llm.factory import get_llm_client
from auto_validator.models.listener import (
    InsightBucket,
    PivotSignal,
    QuizSubmission,
    WeeklyReport,
)
from auto_validator.state.manager import StateManager
from auto_validator.utils.prompt_loader import load_prompt

console = Console()


class ListenerModule:
    """Module C: Data Collection & Analysis — ingest submissions, generate reports."""

    def __init__(self, state_manager: StateManager | None = None) -> None:
        self._llm = get_llm_client()
        self._state = state_manager or StateManager()

    def process_submission(self, submission: QuizSubmission) -> None:
        """Append a quiz submission to the project state."""
        state = self._state.load(submission.project_id)
        state.submissions.append(submission)
        self._state.save(state)
        console.print(f"[dim]Submission recorded for project {submission.project_id}[/dim]")

    def generate_weekly_report(self, project_id: str) -> WeeklyReport:
        """Analyze all submissions and generate a report."""
        state = self._state.load(project_id)

        if not state.submissions:
            console.print("[yellow]No submissions found for this project.[/yellow]")
            return WeeklyReport(
                project_id=project_id,
                lead_count=0,
                avg_pain_score=0.0,
                top_pain_point="No data collected yet.",
                buckets=[],
                pivot_signals=[],
                recommendation_text="No quiz responses have been collected yet. "
                                    "Share your quiz link and check back once you have at least 10 responses.",
            )

        open_answers = [
            s.open_ended_answer for s in state.submissions if s.open_ended_answer.strip()
        ]
        pain_scores = [s.pain_score for s in state.submissions if s.pain_score is not None]
        avg_pain = sum(pain_scores) / len(pain_scores) if pain_scores else 0.0

        # Extract insights
        buckets, pivot_signals = self._extract_insights(
            open_answers,
            idea=state.idea,
        )

        # Generate report text
        now = datetime.now(timezone.utc)
        report_text_data = self._generate_report_text(
            idea=state.idea,
            lead_count=len(state.submissions),
            avg_pain_score=avg_pain,
            buckets=buckets,
            pivot_signals=pivot_signals,
            period_end=now.isoformat(),
        )

        report = WeeklyReport(
            project_id=project_id,
            lead_count=len(state.submissions),
            avg_pain_score=avg_pain,
            top_pain_point=report_text_data.get("top_pain_point", ""),
            buckets=buckets,
            pivot_signals=pivot_signals,
            recommendation_text=report_text_data.get("recommendation_text", ""),
            period_end=now.isoformat(),
        )

        # Persist report
        state.weekly_reports.append(report)
        self._state.save(state)

        # Send email report
        self._send_report_email(report, state.idea)

        return report

    def _extract_insights(
        self, answers: list[str], idea: str
    ) -> tuple[list[InsightBucket], list[PivotSignal]]:
        if not answers:
            return [], []

        console.print(f"[dim]  → Analyzing {len(answers)} open-ended responses...[/dim]")
        system, user = load_prompt(
            "listener", "extract_insights",
            idea=idea,
            count=len(answers),
            answers=answers,
        )
        result = self._llm.complete_json(system, user)
        buckets = [InsightBucket(**b) for b in result.get("buckets", [])]
        pivot_signals = [PivotSignal(**s) for s in result.get("pivot_signals", [])]
        return buckets, pivot_signals

    def _generate_report_text(
        self,
        idea: str,
        lead_count: int,
        avg_pain_score: float,
        buckets: list[InsightBucket],
        pivot_signals: list[PivotSignal],
        period_end: str,
    ) -> dict:
        console.print("[dim]  → Writing weekly report...[/dim]")
        system, user = load_prompt(
            "listener", "generate_report",
            idea=idea,
            lead_count=lead_count,
            avg_pain_score=round(avg_pain_score, 1),
            buckets=[b.model_dump() for b in buckets],
            pivot_signals=[s.model_dump() for s in pivot_signals],
            period_start="",
            period_end=period_end[:10],
        )
        return self._llm.complete_json(system, user)

    def _send_report_email(self, report: WeeklyReport, idea: str) -> None:
        from auto_validator.integrations.sendgrid import SendGridIntegration
        from auto_validator.models.closer import Email

        email = Email(
            subject=f"Weekly Validation Report — {idea[:30]}",
            preview_text=f"{report.lead_count} leads. Top insight: {report.top_pain_point[:50]}",
            body_text=report.recommendation_text,
            body_html=f"<p>{report.recommendation_text.replace(chr(10), '</p><p>')}</p>",
        )
        try:
            sg = SendGridIntegration()
            from auto_validator.config import settings
            sg.send_email(settings.from_email, email)
        except IntegrationError as exc:
            console.print(f"[yellow]Report email skipped: {exc}[/yellow]")

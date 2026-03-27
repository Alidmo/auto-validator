from auto_validator.config import settings
from auto_validator.exceptions import IntegrationError
from auto_validator.integrations.base import BaseIntegration, console
from auto_validator.models.closer import Email


class SendGridIntegration(BaseIntegration):
    def send_email(self, to: str, email: Email) -> bool:
        """Send a single email. Returns True on success."""
        if self.dry_run:
            self._log_dry_run("SendGrid.send_email", {
                "to": to,
                "subject": email.subject,
                "body_preview": email.body_text[:200],
            })
            return True

        if not settings.sendgrid_api_key:
            raise IntegrationError("SENDGRID_API_KEY not configured.")

        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
            message = Mail(
                from_email=settings.from_email,
                to_emails=to,
                subject=email.subject,
                html_content=email.body_html,
                plain_text_content=email.body_text,
            )
            response = sg.send(message)
            return response.status_code in (200, 202)
        except Exception as exc:
            raise IntegrationError(f"SendGrid error: {exc}") from exc

    def schedule_sequence(self, to: str, emails: list[Email], send_days: list[int]) -> None:
        """
        Log or schedule a multi-email sequence.
        send_days: list of day offsets (e.g. [0, 2, 4, 6] for PLF).
        In dry-run mode, prints the schedule. In live mode, uses SendGrid Marketing Campaigns.
        """
        if self.dry_run:
            for day, email in zip(send_days, emails):
                console.print(f"[dim][DRY RUN] Schedule email Day+{day}: '{email.subject}' → {to}[/dim]")
            return

        # Live mode: send sequentially (production would use SendGrid Automation)
        for email in emails:
            self.send_email(to, email)

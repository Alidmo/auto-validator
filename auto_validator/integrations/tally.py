import json
from pathlib import Path

import httpx

from auto_validator.config import settings
from auto_validator.exceptions import IntegrationError
from auto_validator.integrations.base import BaseIntegration, console
from auto_validator.models.creative import QuizQuestion, QuestionType


def _build_tally_payload(questions: list[QuizQuestion], title: str) -> dict:
    """Convert our QuizQuestion models to a Tally-compatible structure."""
    fields = []
    for q in questions:
        if q.question_type == QuestionType.OPEN_ENDED:
            field_type = "TEXTAREA"
        elif q.question_type == QuestionType.PAIN_SCALE:
            field_type = "RATING"
        else:
            field_type = "MULTIPLE_CHOICE"

        field: dict = {
            "uuid": q.question_id,
            "type": field_type,
            "title": q.question_text,
            "isRequired": q.required,
        }
        if q.options and q.question_type != QuestionType.PAIN_SCALE:
            field["options"] = [{"id": str(i), "text": opt} for i, opt in enumerate(q.options)]

        fields.append(field)

    return {"title": title, "fields": fields, "status": "DRAFT"}


class TallyIntegration(BaseIntegration):
    def create_quiz(self, questions: list[QuizQuestion], title: str) -> str:
        """Push quiz to Tally.so. Returns the form ID (or mock ID in dry-run)."""
        payload = _build_tally_payload(questions, title)

        # Always export JSON to disk for manual import
        export_path = settings.output_dir / "exports" / f"quiz_{title[:30].replace(' ', '_')}.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[dim]Quiz JSON exported to: {export_path}[/dim]")

        if self.dry_run:
            self._log_dry_run("Tally.create_quiz", {"title": title, "question_count": len(questions)})
            return "[DRY RUN] tally-form-mock-id"

        if not settings.tally_api_key:
            raise IntegrationError("TALLY_API_KEY not configured.")

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.tally.so/forms",
                    headers={
                        "Authorization": f"Bearer {settings.tally_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                return response.json().get("id", "unknown")
        except Exception as exc:
            raise IntegrationError(f"Tally API error: {exc}") from exc

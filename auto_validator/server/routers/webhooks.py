import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from auto_validator.models.listener import QuizSubmission
from auto_validator.modules.listener import ListenerModule
from auto_validator.server.dependencies import get_listener_module
from auto_validator.state.manager import StateManager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_tally_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Tally webhook."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/tally/{project_id}")
async def tally_webhook(
    project_id: str,
    request: Request,
    listener: ListenerModule = Depends(get_listener_module),
) -> dict:
    """Receive Tally.so quiz submissions."""
    body = await request.body()
    payload = json.loads(body)

    # Verify signature if secret is configured
    try:
        state = StateManager().load(project_id)
        if state.listener_config and state.listener_config.webhook_secret:
            sig = request.headers.get("tally-signature", "")
            if not _verify_tally_signature(body, sig, state.listener_config.webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid signature")
    except Exception:
        pass  # No secret configured — accept all

    # Parse Tally payload
    fields = payload.get("data", {}).get("fields", [])
    answers = {}
    open_ended = ""
    pain_score = None

    for field in fields:
        fid = field.get("key", "")
        value = field.get("value", "")
        answers[fid] = value

        # Detect open-ended (textarea) answers
        if field.get("type") == "TEXTAREA":
            open_ended = str(value)
        # Detect pain scale (rating)
        elif field.get("type") == "RATING":
            try:
                pain_score = int(value)
            except (ValueError, TypeError):
                pass

    submission = QuizSubmission(
        project_id=project_id,
        respondent_id=payload.get("data", {}).get("respondentId", ""),
        answers=answers,
        open_ended_answer=open_ended,
        pain_score=pain_score,
        qualified=True,
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )

    listener.process_submission(submission)
    return {"status": "ok"}


@router.post("/typeform/{project_id}")
async def typeform_webhook(
    project_id: str,
    request: Request,
    listener: ListenerModule = Depends(get_listener_module),
) -> dict:
    """Receive Typeform quiz submissions."""
    payload = await request.json()
    answers = {}
    open_ended = ""
    pain_score = None

    for answer in payload.get("form_response", {}).get("answers", []):
        field_id = answer.get("field", {}).get("ref", "")
        field_type = answer.get("type", "")

        if field_type == "text":
            value = answer.get("text", "")
            answers[field_id] = value
            open_ended = value
        elif field_type == "number":
            value = answer.get("number", 0)
            answers[field_id] = value
            pain_score = int(value)
        elif field_type == "choice":
            answers[field_id] = answer.get("choice", {}).get("label", "")
        else:
            answers[field_id] = str(answer)

    submission = QuizSubmission(
        project_id=project_id,
        respondent_id=payload.get("form_response", {}).get("token", ""),
        answers=answers,
        open_ended_answer=open_ended,
        pain_score=pain_score,
        qualified=True,
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )

    listener.process_submission(submission)
    return {"status": "ok"}

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Auto-Validator** is an autonomous market research and business idea validation system. It takes a single-sentence business idea and outputs a complete validated funnel: ad copy, landing page, quiz logic, email sequences, and data-backed analysis reports.

## Setup & Commands

```bash
# Install (editable mode)
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Get a FREE Gemini API key at https://aistudio.google.com/apikey (no billing required)
# Set GEMINI_API_KEY=your-key-here in .env. DRY_RUN=true by default.

# Run tests
pytest

# Run a single test file
pytest tests/test_utils/test_cvr_logic.py -v

# Sprint 1: Full pipeline, no external APIs needed (DRY_RUN=true)
auto-validator run --idea "A productivity app for kindergarten teachers" --auto

# Start the webhook listener server (Module C)
uvicorn auto_validator.server.app:app --reload --port 8000

# Update metrics and trigger smart CVR logic
auto-validator metrics update --project-id <id> --clicks 100 --leads 25

# Generate weekly insight report from quiz submissions
auto-validator listener report --project-id <id>

# Simulate quiz responses (for testing the analysis pipeline)
auto-validator listener simulate --project-id <id> --count 30

# Approve launch and generate PLF 4-email sequence
auto-validator closer approve-launch --project-id <id>

# List all projects
auto-validator projects list
```

## Architecture

### 4 Business Modules

**Module A – `auto_validator/modules/strategist.py`** (Hypothesis Engine)
- Input: raw one-sentence business idea
- LLM pipeline: generate 3 angles → choose angle (interactive or auto) → create customer avatar → score Timeless Equation (People + Problem + Solution + Message)
- Smart loop: if `pain_score < min_pain_score` (default 5/10), calls `refine_niche` prompt and retries (max 3x). Raises `ValidationLoopError` on exhaustion.
- Returns `StrategistOutput`

**Module B – `auto_validator/modules/creative.py`** (Asset Generation)
- Sequential pipeline: ad hooks → visual prompts → landing page copy → quiz questions
- Calls integrations (all dry-run safe): DALL-E → Google Docs → Tally.so
- Falls back to local Markdown export if Google Docs unavailable
- Returns `CreativeOutput`

**Module C – `auto_validator/modules/listener.py`** (Data Collection & Analysis)
- `process_submission()`: appends quiz submissions to project state
- `generate_weekly_report()`: batches all open-ended answers → LLM extracts insight buckets and pivot signals → generates report text → sends via SendGrid
- Exposed via FastAPI webhooks at `POST /webhooks/tally/{project_id}` and `POST /webhooks/typeform/{project_id}`

**Module D – `auto_validator/modules/closer.py`** (Launch Sequence)
- `generate_thank_you()`: LLM writes warm thank-you email
- `approve_launch()`: generates PLF 4-email sequence (curiosity → backstory → logic → open cart)

### Smart CVR Logic (`auto_validator/utils/cvr_logic.py`)
Pure function `evaluate_cvr(metrics) -> (status_tag, actions)`:
- CVR > 20% → `"Validated"` + `["draft_scaling_ads"]`
- CVR < 5% + landing page drop-off → `"Refinement"` + `["rewrite_headline"]`
- CVR < 5% + quiz drop-off → `"Refinement"` + `["simplify_quiz"]`

### Key Structural Patterns

**State**: `ProjectState` (Pydantic model in `models/project.py`) is the single serializable object that flows through all modules. Persisted to `~/.auto-validator/projects/{id}.json` by default, or Supabase when `SUPABASE_URL` is set. `StateManager` (`state/manager.py`) auto-selects backend.

**LLM**: `LLMClient` abstract base (`llm/base.py`) with `OpenAIClient` and `OllamaClient` implementations. `get_llm_client()` factory reads `LLM_PROVIDER` env var. All modules call `self._llm.complete(system, user, ResponseModel)` — returns a validated Pydantic object.

**Prompts**: All in `auto_validator/prompts/{module}/{name}.yaml` as YAML with `system:` and `user:` blocks. Variables are Jinja2 `{{ variable }}` placeholders. Loaded via `utils/prompt_loader.load_prompt(module, name, **kwargs)`.

**Integrations**: All five (`google_docs`, `tally`, `sendgrid`, `dalle`, `supabase_store`) inherit from `integrations/base.py`. `self.dry_run` reads `settings.dry_run`. When `True`, prints what would happen and returns mock values — no external calls.

### Sprint Progression
- **Sprint 1**: `DRY_RUN=true` + any LLM → full pipeline runs, exports Markdown to `output/exports/`
- **Sprint 2**: Set `GOOGLE_CREDENTIALS_PATH`, `TALLY_API_KEY`, `SENDGRID_API_KEY`, `DRY_RUN=false` → live funnel
- **Sprint 3**: Run uvicorn server, point Tally webhook to `/webhooks/tally/{project_id}`
- **Sprint 4**: Set `SUPABASE_URL` + `SUPABASE_KEY` → state auto-migrates to Supabase

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | Python (replaces n8n) |
| LLM (default, free) | Gemini 2.5 Flash via Google AI Studio free API key |
| LLM (local, free) | Llama 3 via Ollama |
| LLM (paid) | OpenAI GPT-4o |
| Image generation | OpenAI DALL-E 3 (`DALLE_ENABLED=true`, paid) |
| Database/State | Supabase or local JSON files |
| Forms | Tally.so or Typeform |
| Email | SendGrid |
| Webhook server | FastAPI + uvicorn |
| CLI | Click + Rich |

> **Note on subscriptions:** Claude Pro and Gemini Advanced are consumer chat products — neither gives API access. The Gemini free tier (`aistudio.google.com/apikey`) is a separate, truly free developer API.

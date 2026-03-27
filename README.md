# Auto-Validator

> Autonomous business idea validation — from a single sentence to a fully validated marketing funnel, powered by LLMs and real conversion data.

[![PyPI](https://img.shields.io/pypi/v/auto-validator.svg)](https://pypi.org/project/auto-validator/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/your-username/auto-validator/actions/workflows/test.yml/badge.svg)](https://github.com/your-username/auto-validator/actions)

Auto-Validator is a Python CLI and webhook server that takes a one-sentence business idea and runs it through a four-stage autonomous pipeline: strategic validation, marketing asset generation, live data collection, and launch sequencing. It is built for developers and entrepreneurs who want to test whether an idea has real market demand before investing time or money in building it.

---

## Zero to Validated in 2 Minutes

Get a free Gemini API key ([no billing required](https://aistudio.google.com/apikey)), then:

```bash
# Option A — run without installing (requires uv)
GEMINI_API_KEY=your-key uvx auto-validator run --idea "A habit tracker for remote engineers" --auto

# Option B — install once, use anywhere
pipx install auto-validator
# or: uv tool install auto-validator

GEMINI_API_KEY=your-key auto-validator run --idea "A habit tracker for remote engineers" --auto
```

Don't have `uv` or `pipx`? Install one:
```bash
# uv (recommended — fast, modern)
curl -LsSf https://astral.sh/uv/install.sh | sh

# pipx (classic)
pip install pipx
```

Your validated funnel — ad hooks, landing page copy, quiz questions, and a customer avatar — exports to Markdown. No external API calls unless you configure them (`DRY_RUN=true` by default).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Webhook Server](#webhook-server)
- [Sprint Progression](#sprint-progression)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Testing](#testing)
- [Contributing](#contributing)

---

## Overview

Most business ideas fail not because the product was bad, but because no one validated the market first. Auto-Validator automates the validation loop that experienced marketers run manually: find the right angle, write compelling copy, put it in front of an audience, collect data, and decide whether to launch or pivot.

The system is designed as four sequential business modules:

1. **Strategist** — Scores your idea against the Timeless Equation and refines the niche if needed
2. **Creative** — Generates ad copy, landing page content, and a quiz funnel
3. **Listener** — Collects real quiz responses via webhooks and extracts insight patterns
4. **Closer** — Generates a Product Launch Formula email sequence when you are ready to launch

Each module is independently usable via CLI. All external integrations (Google Docs, Tally.so, SendGrid, DALL-E) are dry-run safe by default, so the full pipeline runs without credentials.

---

## Features

- **Free to start** — the default LLM is Gemini 2.0 Flash, which uses Google AI Studio's free developer API tier
- **Fully autonomous** — run with `--auto` and the pipeline completes without prompts
- **Interactive angle selection** — run without `--auto` to choose between three LLM-generated marketing angles
- **Smart niche refinement** — if the pain score falls below a threshold, the strategist refines the idea and retries automatically (up to 3 times)
- **Smart CVR logic** — a pure `evaluate_cvr()` function classifies your funnel as Validated, Monitoring, or Refinement and prescribes the next action
- **Swap LLMs via env var** — switch between Gemini, OpenAI GPT-4o, and local Ollama without changing code
- **YAML prompt templates** — all LLM prompts are Jinja2-templated YAML files you can edit without touching Python
- **Dry-run safe integrations** — every external call prints what it would do when `DRY_RUN=true`
- **Portable state** — projects are stored as JSON files locally or in Supabase when configured

---

## Architecture

Auto-Validator is organized around four business modules that share a single `ProjectState` Pydantic model. State flows through each module and is persisted after every step so you can resume a project at any point.

```
Business Idea (one sentence)
        │
        ▼
┌───────────────────┐
│  Module A         │  Generates 3 marketing angles → picks one
│  Strategist       │  Creates customer avatar
│  (Hypothesis)     │  Scores Timeless Equation (People + Problem +
│                   │  Solution + Message, each 1–10)
│                   │  Refines niche if pain_score < 5, retries up to 3x
└────────┬──────────┘
         │  StrategistOutput
         ▼
┌───────────────────┐
│  Module B         │  Ad hooks → visual prompts → landing page copy
│  Creative         │  → quiz questions
│  (Asset Gen)      │  Publishes to Google Docs + Tally (or Markdown)
└────────┬──────────┘
         │  CreativeOutput
         ▼
┌───────────────────┐
│  Module C         │  FastAPI webhook server receives form submissions
│  Listener         │  Batches open-ended answers → LLM insight report
│  (Data)           │  Smart CVR logic: >20% = Validated, <5% = Refinement
│                   │  Sends weekly reports via SendGrid
└────────┬──────────┘
         │  Validated signal
         ▼
┌───────────────────┐
│  Module D         │  PLF 4-email sequence:
│  Closer           │  Curiosity → Backstory → Logic → Open Cart
│  (Launch)         │  Thank-you email for quiz completions
└───────────────────┘
```

### Smart CVR Logic

The `evaluate_cvr(metrics)` function in `auto_validator/utils/cvr_logic.py` is a pure function — no side effects, fully testable — that classifies your funnel and prescribes the next action:

| CVR Range | Drop-off Location | Status | Prescribed Action |
|-----------|-------------------|--------|-------------------|
| > 20% | — | `Validated` | `draft_scaling_ads` |
| < 5% | Landing page | `Refinement` | `rewrite_headline` |
| < 5% | Quiz | `Refinement` | `simplify_quiz` |
| 5%–20% | — | `Monitoring` | (collect more data) |

### LLM Abstraction

`LLMClient` is an abstract base class. You swap providers by setting `LLM_PROVIDER` in your environment — no code changes required.

```
LLMClient (abstract)
├── GeminiClient           ← default, free API (aistudio.google.com)
├── OllamaClient           ← local Llama 3, no API key, no internet
├── OpenAICompatibleClient ← Groq (free tier), LM Studio, Together.ai, Fireworks...
├── OpenAIClient           ← GPT-4o (paid)
└── AnthropicClient        ← Claude (paid, pip install anthropic)
```

To add a new provider: implement `_raw_complete(system, user, temperature) -> str` in a subclass and register it in `llm/factory.py`. The JSON parsing, retry logic, and Pydantic validation all live in the base class.

### Prompt System

Every LLM call is driven by a YAML file in `auto_validator/prompts/{module}/{name}.yaml`:

```yaml
system: |
  You are a direct-response marketing strategist...

user: |
  Idea: {{ idea }}
  Analyze this idea and generate three distinct marketing angles.
```

Variables use Jinja2 syntax. To change how the LLM behaves, edit the YAML — you never need to touch Python.

---

## Installation

### Recommended — `pipx` or `uv tool` (isolated, no virtual env needed)

```bash
# Using pipx
pipx install auto-validator

# Using uv
uv tool install auto-validator
```

Both install `auto-validator` as a global command without polluting your system Python.

### Run without installing — `uvx`

```bash
uvx auto-validator --help
```

`uvx` downloads and runs the package in a temporary environment. Useful for one-off runs.

### From source (for development)

```bash
git clone https://github.com/your-username/auto-validator.git
cd auto-validator
pip install -e ".[dev]"
```

### Verify

```bash
auto-validator --help
```

---

## Configuration

Copy the example environment file and open it in your editor:

```bash
cp .env.example .env
```

### Minimum Configuration (free options)

**Gemini (recommended — free, 250 req/day):**
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here   # https://aistudio.google.com/apikey
DRY_RUN=true
```

**Groq (free tier, fast):**
```env
LLM_PROVIDER=openai-compatible
OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1
OPENAI_COMPATIBLE_API_KEY=gsk_your_groq_key
OPENAI_COMPATIBLE_MODEL=llama-3.3-70b-versatile
DRY_RUN=true
```

**Ollama (fully local, no internet):**
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3
DRY_RUN=true
```

> **Note:** Google AI Studio (`aistudio.google.com`) is a free developer API, completely separate from Gemini Advanced (the consumer subscription). No paid plan needed.

### Full Environment Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | `gemini` · `ollama` · `openai-compatible` · `openai` · `anthropic` |
| `GEMINI_API_KEY` | — | Free key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `OPENAI_COMPATIBLE_BASE_URL` | — | Any OpenAI-compatible endpoint (Groq, LM Studio…) |
| `OPENAI_COMPATIBLE_API_KEY` | — | API key for the compatible endpoint |
| `OPENAI_COMPATIBLE_MODEL` | — | Model name to use (provider-specific) |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` | Anthropic model name |
| `DRY_RUN` | `true` | When `true`, no external API calls are made |
| `DALLE_ENABLED` | `false` | Enable DALL-E image generation (requires OpenAI key) |
| `GOOGLE_CREDENTIALS_PATH` | `credentials.json` | Path to Google OAuth credentials JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | — | Google Drive folder for exported docs |
| `TALLY_API_KEY` | — | Tally.so API key for quiz creation |
| `SENDGRID_API_KEY` | — | SendGrid key for email delivery |
| `FROM_EMAIL` | `noreply@auto-validator.com` | Sender address for outgoing emails |
| `SUPABASE_URL` | — | Supabase project URL (leave blank for local JSON) |
| `SUPABASE_KEY` | — | Supabase anon/service key |
| `CVR_VALIDATED_THRESHOLD` | `0.20` | CVR above this → Validated |
| `CVR_REFINEMENT_THRESHOLD` | `0.05` | CVR below this → Refinement |
| `MAX_REFINEMENT_RETRIES` | `3` | Max niche refinement loops before raising an error |
| `MIN_PAIN_SCORE` | `5` | Minimum Timeless Equation pain score (1–10) |
| `WEBHOOK_HOST` | `0.0.0.0` | Host for the FastAPI webhook server |
| `WEBHOOK_PORT` | `8000` | Port for the FastAPI webhook server |

---

## Usage

### Run the Full Pipeline

```bash
# Fully automated (no prompts)
auto-validator run --idea "A meal planning app for athletes cutting weight" --auto

# Interactive — choose your marketing angle
auto-validator run --idea "A meal planning app for athletes cutting weight"
```

The pipeline saves all outputs to `output/exports/` as Markdown and persists project state to `~/.auto-validator/projects/{id}.json`.

### Discover Ideas for a Market

```bash
auto-validator discover --market "productivity tools for remote workers"
```

### Manage Projects

```bash
# List all projects with status
auto-validator projects list

# Show details for a specific project
auto-validator projects show --project-id <id>
```

### Update Metrics and Check CVR Status

After your landing page and quiz go live, feed in click and lead counts to trigger CVR analysis:

```bash
# Record traffic data
auto-validator metrics update --project-id <id> --clicks 450 --leads 112

# Check current status and prescribed action
auto-validator metrics status --project-id <id>
```

Example output:

```
Status:  Validated
CVR:     24.9%
Action:  draft_scaling_ads
```

### Generate a Weekly Insight Report

Processes all quiz submissions collected since the last report, extracts insight buckets and pivot signals via LLM, and sends the report via SendGrid (or prints it in dry-run mode):

```bash
auto-validator listener report --project-id <id>
```

### Simulate Quiz Submissions (for Testing)

Generates synthetic quiz responses so you can test the analysis pipeline without live traffic:

```bash
auto-validator listener simulate --project-id <id> --count 30
```

### Approve Launch and Generate Email Sequence

When CVR signals a validated idea, generate the four-email Product Launch Formula sequence:

```bash
auto-validator closer approve-launch --project-id <id>
```

This produces four emails — Curiosity, Backstory, Logic, and Open Cart — exported to Markdown and optionally delivered via SendGrid.

---

## Webhook Server

Module C runs as a FastAPI server that receives quiz submissions from Tally.so or Typeform in real time.

### Start the Server

```bash
uvicorn auto_validator.server.app:app --reload --port 8000
```

### Webhook Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/tally/{project_id}` | Receive Tally.so form submissions |
| `POST` | `/webhooks/typeform/{project_id}` | Receive Typeform submissions |
| `GET` | `/health` | Health check |

### Connecting Tally.so

1. Create your quiz form in Tally.so
2. In Tally settings, add a webhook pointing to `https://your-domain.com/webhooks/tally/{project_id}`
3. Start the uvicorn server (or deploy it to a server with a public URL)
4. Submissions will be stored and included in the next weekly report

For local development, use [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 8000
# Use the ngrok HTTPS URL as your Tally webhook target
```

---

## Sprint Progression

Auto-Validator is designed to be adopted incrementally. Each sprint adds one layer of live integration on top of the previous dry-run baseline.

### Sprint 1 — Full Pipeline, No Credentials

Everything runs locally. Assets are exported to Markdown. No external calls.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
DRY_RUN=true
```

```bash
auto-validator run --idea "your idea" --auto
# Output: output/exports/{project-id}/
```

### Sprint 2 — Live Funnel Assets

Assets are published to Google Docs and the quiz is created in Tally.so. Emails are sent via SendGrid.

```env
DRY_RUN=false
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
TALLY_API_KEY=your-tally-key
SENDGRID_API_KEY=your-sendgrid-key
FROM_EMAIL=you@yourdomain.com
```

### Sprint 3 — Live Data Collection

Start the webhook server and point your Tally form at it. Real submissions flow into the analysis pipeline.

```bash
uvicorn auto_validator.server.app:app --reload --port 8000
```

### Sprint 4 — Cloud State

State auto-migrates from local JSON to Supabase. Projects survive machine reboots and can be shared across team members.

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

No code changes are required between sprints. The `StateManager` detects which backend to use based on which environment variables are set.

---

## Project Structure

```
auto_validator/
├── cli/                  # Click CLI entry points and command groups
├── config.py             # Pydantic settings, reads from .env
├── exceptions.py         # ValidationLoopError and other domain exceptions
├── integrations/
│   ├── base.py           # Abstract integration with dry_run guard
│   ├── dalle.py          # DALL-E 3 image generation
│   ├── google_docs.py    # Google Docs publish
│   ├── sendgrid.py       # Email delivery
│   ├── supabase_store.py # Supabase state backend
│   └── tally.py          # Tally.so form creation
├── llm/
│   ├── base.py           # LLMClient abstract base
│   ├── factory.py        # get_llm_client() — reads LLM_PROVIDER env var
│   ├── gemini.py         # Google Gemini implementation
│   ├── openai_client.py  # OpenAI GPT-4o implementation
│   └── ollama.py         # Ollama local LLM implementation
├── models/               # Pydantic v2 data models for all modules
├── modules/
│   ├── strategist.py     # Module A: angles, avatar, Timeless Equation
│   ├── creative.py       # Module B: ad hooks, landing page, quiz
│   ├── listener.py       # Module C: webhook ingestion, weekly report
│   └── closer.py         # Module D: PLF email sequence
├── prompts/              # YAML prompt templates (Jinja2)
│   ├── strategist/       # generate_angles, create_avatar, validate_equation, refine_niche
│   ├── creative/         # ad_hooks, visual_prompts, landing_page, quiz_questions
│   ├── listener/         # insight_report, pivot_signals
│   └── closer/           # thank_you, plf_sequence
├── server/
│   ├── app.py            # FastAPI application factory
│   └── routers/          # Webhook route handlers
├── state/
│   ├── manager.py        # StateManager — selects JSON or Supabase backend
│   └── json_store.py     # Local JSON file implementation
└── utils/
    ├── cvr_logic.py      # evaluate_cvr() — pure function, no side effects
    ├── prompt_loader.py  # Loads and renders YAML prompts with Jinja2
    ├── markdown_export.py # Writes project outputs to output/exports/
    └── rich_formatter.py  # Rich console output helpers

tests/
├── conftest.py
├── test_modules/         # Unit tests for all four business modules
├── test_utils/           # Tests for CVR logic and prompt loader
└── test_integrations/    # Dry-run integration tests
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| CLI | [Click](https://click.palletsprojects.com/) + [Rich](https://github.com/Textualize/rich) |
| API Server | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) |
| Data Models | [Pydantic v2](https://docs.pydantic.dev/latest/) |
| Settings | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Prompt Templates | [Jinja2](https://jinja.palletsprojects.com/) + YAML |
| LLM (default, free) | [Gemini 2.0 Flash](https://aistudio.google.com) via Google AI Studio |
| LLM (local, free) | [Llama 3](https://ollama.com/library/llama3) via [Ollama](https://ollama.com) |
| LLM (paid) | [OpenAI GPT-4o](https://platform.openai.com) |
| Image Generation | [DALL-E 3](https://platform.openai.com/docs/guides/images) (optional, paid) |
| Forms | [Tally.so](https://tally.so) or [Typeform](https://typeform.com) |
| Email | [SendGrid](https://sendgrid.com) |
| Database | [Supabase](https://supabase.com) or local JSON files |
| HTTP Client | [httpx](https://www.python-httpx.org/) |
| Retry Logic | [tenacity](https://tenacity.readthedocs.io/) |
| Testing | pytest + pytest-asyncio + pytest-mock |

---

## Testing

```bash
# Run the full test suite
pytest

# Run a specific test file with verbose output
pytest tests/test_utils/test_cvr_logic.py -v

# Run only dry-run integration tests
pytest tests/test_integrations/ -v

# Run with output captured (useful for debugging LLM mock responses)
pytest -s
```

All tests run with `DRY_RUN=true` and mocked LLM responses — no API keys or network access required.

---

## Contributing

Contributions are welcome. The most useful areas for contribution are:

- New LLM provider implementations (add a file to `auto_validator/llm/` implementing `LLMClient`)
- New integrations (add a file to `auto_validator/integrations/` extending `BaseIntegration`)
- Prompt improvements (edit YAML files in `auto_validator/prompts/` — no Python required)
- Additional CLI commands and metric analysis features

### Development Setup

```bash
git clone https://github.com/your-username/auto-validator.git
cd auto-validator
pip install -e ".[dev]"
cp .env.example .env
# Set GEMINI_API_KEY in .env
pytest   # All tests should pass before you start making changes
```

### Adding a New LLM Provider

1. Create `auto_validator/llm/your_provider.py` implementing `LLMClient`
2. Register it in `auto_validator/llm/factory.py`
3. Add the provider name to the `LLM_PROVIDER` documentation in `.env.example`
4. Add tests in `tests/test_modules/` with a mocked client

### Adding a New Integration

1. Create `auto_validator/integrations/your_service.py` extending `BaseIntegration`
2. Implement the dry-run guard using `self.dry_run` (inherited from `BaseIntegration`)
3. Add the relevant environment variables to `auto_validator/config.py` and `.env.example`
4. Add a dry-run test in `tests/test_integrations/`

For detailed documentation on each external service integration, see [docs/services.md](docs/services.md).

---

## License

MIT — see [LICENSE](LICENSE) for details.

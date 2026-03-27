# External Service Integrations

Auto-Validator integrates with six external services. Every integration inherits from `BaseIntegration` in `auto_validator/integrations/base.py`, which provides a `self.dry_run` guard. When `DRY_RUN=true` (the default), every integration prints what it would do and returns a mock value — no network calls are made.

This document covers setup, environment variables, dry-run behavior, and known limitations for each service.

---

## Table of Contents

- [Google Gemini (LLM)](#google-gemini-llm)
- [OpenAI (LLM + Image Generation)](#openai-llm--image-generation)
- [Ollama (Local LLM)](#ollama-local-llm)
- [Google Docs](#google-docs)
- [Tally.so](#tallyso)
- [SendGrid](#sendgrid)
- [Supabase](#supabase)

---

## Google Gemini (LLM)

**Used for:** All LLM completions when `LLM_PROVIDER=gemini` (the default). Powers every prompt in every module — angle generation, avatar creation, Timeless Equation scoring, ad copy, landing page copy, quiz generation, insight reports, and email sequences.

**Why it is the default:** Google AI Studio provides a free developer API tier with no billing setup required. The free quota is sufficient to run dozens of full pipeline runs per day.

### Setup

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) and sign in with a Google account.
2. Click "Create API key" and copy the key.
3. Add it to your `.env` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Set to `gemini` to use this provider |
| `GEMINI_API_KEY` | — | Required. Your Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model to use. `gemini-2.0-flash` is fast and free |

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
```

### Dry-Run Behavior

Gemini is an LLM provider, not an integration — it is called directly by the modules. When `DRY_RUN=true`, the modules themselves skip live LLM calls and use canned fixture responses. Your `GEMINI_API_KEY` is not required in dry-run mode.

### Limitations

- The free tier has rate limits (requests per minute and per day). If you hit rate limits, wait a minute and retry or switch to `GEMINI_MODEL=gemini-2.0-flash-lite` for lighter usage.
- The free tier may not be available in all regions. Check [Google AI Studio availability](https://ai.google.dev/available_regions) if you encounter access errors.
- The free tier is subject to Google's data usage policies for improving models. If this matters for your use case, use a paid tier or a local model.

---

## OpenAI (LLM + Image Generation)

**Used for:** LLM completions when `LLM_PROVIDER=openai`, and optionally DALL-E 3 image generation for ad visuals when `DALLE_ENABLED=true`.

### Setup

1. Create an account at [https://platform.openai.com](https://platform.openai.com).
2. Add a payment method and create an API key under API Keys.
3. Add the key to your `.env` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Set to `openai` to use GPT-4o as the LLM |
| `OPENAI_API_KEY` | — | Required when using OpenAI. Your platform.openai.com key |
| `OPENAI_MODEL` | `gpt-4o` | Model name. `gpt-4o` is recommended; `gpt-4o-mini` is cheaper |
| `DALLE_ENABLED` | `false` | Set to `true` to generate images with DALL-E 3 |

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
DALLE_ENABLED=true
```

### Using DALL-E Without OpenAI as LLM

You can use Gemini as your LLM and still enable DALL-E for image generation:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
OPENAI_API_KEY=sk-...
DALLE_ENABLED=true
```

The `dalle.py` integration reads `OPENAI_API_KEY` directly, independent of `LLM_PROVIDER`.

### Dry-Run Behavior

When `DRY_RUN=true`:

- **LLM calls** — modules use canned fixture responses; no OpenAI calls are made.
- **DALL-E** — the integration prints `[DRY RUN] Would generate image: {prompt}` and returns a placeholder image path. No API call is made and no charges are incurred.

### Limitations

- OpenAI is a paid service. GPT-4o costs approximately $5 per million input tokens and $15 per million output tokens (check [openai.com/pricing](https://openai.com/pricing) for current rates).
- DALL-E 3 costs approximately $0.04–$0.08 per image at standard quality.
- Rate limits apply based on your usage tier.

---

## Ollama (Local LLM)

**Used for:** LLM completions when `LLM_PROVIDER=ollama`. Runs a model locally on your machine — no API key required, no usage costs, completely private.

### Setup

1. Install Ollama from [https://ollama.com](https://ollama.com).
2. Pull the Llama 3 model (approximately 4.7 GB):

```bash
ollama pull llama3
```

3. Start the Ollama server (it starts automatically on most systems after install):

```bash
ollama serve
```

4. Verify it is running:

```bash
curl http://localhost:11434/api/tags
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Set to `ollama` to use local inference |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL of your Ollama server |
| `OLLAMA_MODEL` | `llama3` | Model to use. Must be pulled with `ollama pull` first |

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Dry-Run Behavior

Same as other LLM providers — when `DRY_RUN=true`, modules use fixture responses and do not call Ollama. No Ollama server is required.

### Limitations

- Ollama runs inference on your local CPU or GPU. Performance depends heavily on your hardware. A machine with at least 16 GB of RAM is recommended for Llama 3 (8B parameter model).
- Output quality is lower than GPT-4o or Gemini 2.0 Flash, particularly for structured JSON extraction. If the pipeline produces validation errors, switch to a larger model (e.g., `ollama pull llama3:70b`) or use a cloud provider.
- Ollama must be running before you invoke any `auto-validator` command that makes LLM calls.

---

## Google Docs

**Used for:** Exporting landing page copy, quiz designs, and ad hook documents to Google Drive as formatted Google Docs. This is Module B's publishing step.

**Fallback:** When Google Docs is unavailable or `DRY_RUN=true`, all assets are exported to `output/exports/{project-id}/` as Markdown files. The pipeline does not fail without Google Docs configured.

### Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com) and create a project.
2. Enable the **Google Docs API** and **Google Drive API** for your project.
3. Create OAuth 2.0 credentials (type: Desktop application) and download the JSON file.
4. Save the credentials file to your project directory and set `GOOGLE_CREDENTIALS_PATH` to its path.
5. On first run with `DRY_RUN=false`, a browser window will open for you to authorize access. The resulting token is cached locally.
6. Create a folder in Google Drive and copy its ID from the URL (the long string after `/folders/`).

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CREDENTIALS_PATH` | `credentials.json` | Path to the downloaded OAuth credentials JSON file |
| `GOOGLE_DRIVE_FOLDER_ID` | — | Google Drive folder ID where docs will be created |

```env
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_DRIVE_FOLDER_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74
```

### Dry-Run Behavior

When `DRY_RUN=true`, the Google Docs integration prints:

```
[DRY RUN] Would create Google Doc: "Landing Page — Habit Tracker for Remote Engineers"
[DRY RUN] Would upload to folder: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74
```

The asset content is written to `output/exports/` instead. No Google API calls are made.

### Limitations

- The OAuth flow requires browser access. On a headless server, you will need to complete the OAuth flow locally first and copy the resulting token file to the server.
- Google Drive API has a quota of 1,000 requests per 100 seconds per user. The pipeline makes at most a few requests per project run, so this limit is not a practical concern.

---

## Tally.so

**Used for:** Creating the quiz/lead capture form automatically based on the questions generated by Module B. When integrated, the created form's webhook URL is configured to point at the Auto-Validator listener server (Module C).

**Fallback:** When Tally is unavailable or `DRY_RUN=true`, the quiz questions are exported to Markdown. You can create the form manually in Tally.so using the exported questions and configure the webhook yourself.

### Setup

1. Create a free account at [https://tally.so](https://tally.so).
2. Go to your account settings and find your API key.
3. Add it to your `.env` file.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TALLY_API_KEY` | — | Your Tally.so API key |

```env
TALLY_API_KEY=tally_...
```

### Connecting the Webhook

After your listener server is running, configure the Tally form webhook:

1. In Tally.so, open your form and go to **Integrations > Webhooks**.
2. Add a webhook with the URL: `https://your-domain.com/webhooks/tally/{project_id}`
3. Set the content type to `application/json`.
4. Save and test the webhook.

For local development, use [ngrok](https://ngrok.com) to get a public URL:

```bash
ngrok http 8000
# Use the HTTPS ngrok URL as your webhook base
```

### Dry-Run Behavior

When `DRY_RUN=true`, the integration prints:

```
[DRY RUN] Would create Tally form: "Habit Tracker Validation Quiz"
[DRY RUN] Would add 5 questions to form
[DRY RUN] Mock form URL: https://tally.so/r/dry-run-mock
```

The quiz questions are written to `output/exports/{project-id}/quiz.md` instead.

### Limitations

- Tally.so's free plan supports unlimited forms but has limits on the number of responses and some integration features. Check [tally.so/pricing](https://tally.so/pricing) for the current limits.
- The API does not support all form features available in the Tally UI. Complex branching logic may need to be configured manually after auto-creation.

---

## SendGrid

**Used for:** Sending weekly insight reports (Module C) and the PLF email sequence (Module D) to subscribers. Also sends thank-you emails to quiz completers.

### Setup

1. Create a free account at [https://sendgrid.com](https://sendgrid.com). The free tier allows 100 emails per day.
2. Complete sender verification for your sending domain or single sender address.
3. Create an API key under **Settings > API Keys** with "Mail Send" permission.
4. Add the key and your verified sender address to `.env`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SENDGRID_API_KEY` | — | Your SendGrid API key (starts with `SG.`) |
| `FROM_EMAIL` | `noreply@auto-validator.com` | Verified sender address or domain |

```env
SENDGRID_API_KEY=SG....
FROM_EMAIL=you@yourdomain.com
```

### Dry-Run Behavior

When `DRY_RUN=true`, the integration prints the full email it would send — subject, recipient, and body — without making any API call:

```
[DRY RUN] Would send email:
  To:      list@yourdomain.com
  From:    you@yourdomain.com
  Subject: Weekly Validation Report — Habit Tracker (Week 3)
  Body:    [full email body printed to console]
```

### Limitations

- The SendGrid free tier is limited to 100 emails per day. For list-based sending (e.g., PLF sequences to many subscribers), you will need a paid plan.
- Sender verification is required before any email can be sent. Attempting to send from an unverified address results in a 403 error.
- SendGrid's deliverability depends on your domain reputation. For best results, set up DKIM and SPF records for your sending domain.

---

## Supabase

**Used for:** Storing project state (`ProjectState`) in a hosted Postgres database instead of local JSON files. Enables multi-machine access, team collaboration, and persistent state across environments.

**Default behavior:** When `SUPABASE_URL` is not set, the `StateManager` uses local JSON files stored in `~/.auto-validator/projects/`. No Supabase account or configuration is needed for Sprints 1–3.

### Setup

1. Create a free project at [https://supabase.com](https://supabase.com).
2. In your project dashboard, go to **Settings > API**.
3. Copy the **Project URL** and the **anon public** key (or service role key for server-side use).
4. Add them to `.env`.

The `StateManager` automatically creates the required table structure on first run when Supabase credentials are present.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | — | Your Supabase project URL (e.g., `https://xyz.supabase.co`) |
| `SUPABASE_KEY` | — | Your Supabase API key (anon key or service role key) |

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Migration from Local JSON

When you add Supabase credentials to a project that previously used local JSON storage, existing project state files in `~/.auto-validator/projects/` are not automatically migrated. To migrate an existing project:

```bash
# Export the current state
auto-validator projects show --project-id <id> --export > project_state.json

# After setting Supabase credentials, re-import
auto-validator projects import --file project_state.json
```

### Dry-Run Behavior

The Supabase integration does not have a dry-run mode in the same way as other integrations, because it is a storage backend rather than an outbound action. When `SUPABASE_URL` is not set, the local JSON backend is used automatically — no Supabase calls are made.

### Limitations

- Supabase free tier projects are paused after one week of inactivity. For production use or continuous webhook ingestion, use a paid plan or keep the project active.
- The `ProjectState` object is serialized as JSON and stored in a single `jsonb` column. This is appropriate for the project's scale. If you need to query individual fields (e.g., find all projects with CVR > 20%), you will need to add a migration to extract those fields into dedicated columns.
- Supabase's anon key is safe to use in server-side code but should not be exposed in client-side JavaScript. Use the service role key for server-side webhook handlers.

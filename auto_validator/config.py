from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider: "gemini" | "openai" | "ollama" | "anthropic" | "openai-compatible"
    llm_provider: str = Field(default="gemini")

    # Gemini — free API key from https://aistudio.google.com (no billing required)
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")

    # OpenAI (paid)
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")

    # Ollama — local, no internet required (https://ollama.com)
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3")

    # Anthropic Claude (paid — pip install anthropic)
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-opus-4-6")

    # Generic OpenAI-compatible endpoint (Groq, Together.ai, LM Studio, etc.)
    openai_compatible_base_url: str = Field(default="")
    openai_compatible_api_key: str = Field(default="")
    openai_compatible_model: str = Field(default="")

    # General
    dry_run: bool = Field(default=True)

    # Google Docs
    google_credentials_path: str = Field(default="credentials.json")
    google_drive_folder_id: str = Field(default="")

    # Tally
    tally_api_key: str = Field(default="")

    # SendGrid
    sendgrid_api_key: str = Field(default="")
    from_email: str = Field(default="noreply@auto-validator.com")

    # Supabase (leave blank for local JSON storage)
    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")

    # CVR smart logic
    cvr_validated_threshold: float = Field(default=0.20)
    cvr_refinement_threshold: float = Field(default=0.05)

    # Validation loop guards
    max_refinement_retries: int = Field(default=3)
    min_pain_score: int = Field(default=5)

    # Image generation
    dalle_enabled: bool = Field(default=False)

    # Storage paths
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".auto-validator" / "projects")
    output_dir: Path = Field(default_factory=lambda: Path("output"))

    # Webhook server
    webhook_host: str = Field(default="0.0.0.0")
    webhook_port: int = Field(default=8000)


settings = Settings()

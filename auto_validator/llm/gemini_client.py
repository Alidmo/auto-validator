"""
Gemini provider via Google AI Studio's OpenAI-compatible endpoint.

Free API key (no billing, no per-token charges):
  https://aistudio.google.com/apikey

Free tier limits (Gemini 2.5 Flash as of 2026):
  - 10 requests/minute
  - 250,000 tokens/minute
  - 250 requests/day
"""
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiClient(LLMClient):
    def __init__(self) -> None:
        from openai import OpenAI

        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set.\n"
                "Get a free key (no billing required) at: https://aistudio.google.com/apikey\n"
                "Then add it to your .env file: GEMINI_API_KEY=your-key-here"
            )

        self._client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url=_GEMINI_BASE_URL,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=30),  # Gemini free tier: 10 rpm
        reraise=True,
    )
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=settings.gemini_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

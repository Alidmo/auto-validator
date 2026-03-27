"""
Generic OpenAI-compatible endpoint provider.

Works with any service that implements the OpenAI Chat Completions API:
  - Groq       (https://groq.com)           LLM_PROVIDER=openai-compatible
  - Together.ai (https://together.ai)        OPENAI_COMPATIBLE_BASE_URL=https://api.together.xyz/v1
  - LM Studio  (https://lmstudio.ai)         OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
  - Fireworks  (https://fireworks.ai)
  - Perplexity (https://www.perplexity.ai)

Example .env:
    LLM_PROVIDER=openai-compatible
    OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1
    OPENAI_COMPATIBLE_API_KEY=gsk_...
    OPENAI_COMPATIBLE_MODEL=llama-3.3-70b-versatile
"""
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient


class OpenAICompatibleClient(LLMClient):
    def __init__(self) -> None:
        from openai import OpenAI

        if not settings.openai_compatible_base_url:
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL is not set.\n"
                "Set it to your provider's OpenAI-compatible endpoint, e.g.:\n"
                "  OPENAI_COMPATIBLE_BASE_URL=https://api.groq.com/openai/v1"
            )
        if not settings.openai_compatible_model:
            raise ValueError(
                "OPENAI_COMPATIBLE_MODEL is not set.\n"
                "Set it to the model name your provider uses, e.g.:\n"
                "  OPENAI_COMPATIBLE_MODEL=llama-3.3-70b-versatile"
            )

        self._client = OpenAI(
            api_key=settings.openai_compatible_api_key or "none",
            base_url=settings.openai_compatible_base_url,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=settings.openai_compatible_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

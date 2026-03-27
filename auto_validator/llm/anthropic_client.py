"""
Anthropic Claude provider.

Install the extra dependency first:
    pip install anthropic

Get an API key at: https://console.anthropic.com
"""
from tenacity import retry, stop_after_attempt, wait_exponential

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient


class AnthropicClient(LLMClient):
    def __init__(self) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for this provider.\n"
                "Install it with: pip install anthropic"
            ) from exc

        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set.\n"
                "Get an API key at: https://console.anthropic.com\n"
                "Then add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )

        self._client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        return response.content[0].text

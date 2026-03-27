from tenacity import retry, stop_after_attempt, wait_exponential

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

import json

import httpx

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient

_JSON_INSTRUCTION = (
    "\n\nIMPORTANT: You MUST respond with valid JSON only. "
    "Do not include any explanation or markdown — pure JSON that matches the requested schema."
)


class OllamaClient(LLMClient):
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt + _JSON_INSTRUCTION},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

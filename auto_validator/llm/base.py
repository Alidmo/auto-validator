import json
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

from auto_validator.exceptions import LLMParseError

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """Abstract LLM client. Subclasses implement _raw_complete."""

    @abstractmethod
    def _raw_complete(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Return raw string response from the LLM."""

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.7,
    ) -> T:
        """Call the LLM and parse the response into response_model."""
        raw = self._raw_complete(system_prompt, user_prompt, temperature)
        try:
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            return response_model.model_validate_json(cleaned)
        except Exception as exc:
            raise LLMParseError(
                f"Could not parse LLM response into {response_model.__name__}.\n"
                f"Raw response:\n{raw}\nError: {exc}"
            ) from exc

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Return raw text (no parsing)."""
        return self._raw_complete(system_prompt, user_prompt, temperature)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> dict:
        """Return parsed dict from JSON response."""
        raw = self._raw_complete(system_prompt, user_prompt, temperature)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMParseError(f"LLM response is not valid JSON: {exc}\nRaw: {raw}") from exc

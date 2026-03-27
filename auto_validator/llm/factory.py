from functools import lru_cache

from auto_validator.config import settings
from auto_validator.llm.base import LLMClient


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        from auto_validator.llm.gemini_client import GeminiClient
        return GeminiClient()
    elif provider == "openai":
        from auto_validator.llm.openai_client import OpenAIClient
        return OpenAIClient()
    elif provider == "ollama":
        from auto_validator.llm.ollama_client import OllamaClient
        return OllamaClient()
    elif provider == "anthropic":
        from auto_validator.llm.anthropic_client import AnthropicClient
        return AnthropicClient()
    elif provider == "openai-compatible":
        from auto_validator.llm.openai_compatible_client import OpenAICompatibleClient
        return OpenAICompatibleClient()
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            "Supported: 'gemini' (free), 'ollama' (local/free), 'openai' (paid), "
            "'anthropic' (paid), 'openai-compatible' (Groq/Together/LM Studio)."
        )

"""MaaS client for DeepSeek Flash. API credentials are read only from the environment."""

import os
from dataclasses import dataclass

import httpx

MAAS_API_URL = "https://maas.bit.edu.cn/v1/chat/completions"
MAAS_MODEL_NAME = "deepseek-v4-flash"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL_NAME = "deepseek/deepseek-v4-flash"


class LLMServiceError(RuntimeError):
    """Raised when the MaaS API cannot return a usable answer."""


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    api_url: str
    model: str
    api_key: str


def get_llm_config() -> LLMProviderConfig:
    """Read the active provider from environment variables without exposing its API key."""
    provider = os.getenv("LLM_PROVIDER", "maas").strip().lower()
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        default_url = OPENROUTER_API_URL
        default_model = OPENROUTER_MODEL_NAME
        key_name = "OPENROUTER_API_KEY"
    elif provider == "maas":
        api_key = os.getenv("GPUSTACK_API_KEY")
        default_url = MAAS_API_URL
        default_model = MAAS_MODEL_NAME
        key_name = "GPUSTACK_API_KEY"
    else:
        raise LLMServiceError("LLM_PROVIDER must be either 'maas' or 'openrouter'")
    if not api_key:
        raise LLMServiceError(f"{key_name} is not configured")
    return LLMProviderConfig(
        provider=provider,
        api_url=os.getenv("LLM_BASE_URL", default_url),
        model=os.getenv("LLM_MODEL", default_model),
        api_key=api_key,
    )


def get_active_model_name() -> str:
    return get_llm_config().model


async def chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """Call the school MaaS chat-completions endpoint without exposing secrets."""
    config = get_llm_config()
    headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
    payload = {"model": config.model, "messages": messages, "temperature": temperature}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(config.api_url, headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        response_preview = exc.response.text[:300].replace("\n", " ")
        raise LLMServiceError(
            f"{config.provider} API returned HTTP {exc.response.status_code}: {response_preview or 'no response detail'}"
        ) from exc
    except httpx.RequestError as exc:
        detail = str(exc) or repr(exc)
        raise LLMServiceError(f"{config.provider} API transport error ({exc.__class__.__name__}): {detail}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMServiceError("MaaS API returned an unexpected response") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMServiceError("MaaS API returned empty content")
    return content.strip()

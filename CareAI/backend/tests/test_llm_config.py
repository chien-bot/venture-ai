from app.services.llm import (
    MAAS_API_URL,
    MAAS_MODEL_NAME,
    OPENROUTER_API_URL,
    OPENROUTER_MODEL_NAME,
    get_llm_config,
)


def test_maas_is_the_default_provider(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GPUSTACK_API_KEY", "test-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = get_llm_config()

    assert config.provider == "maas"
    assert config.api_url == MAAS_API_URL
    assert config.model == MAAS_MODEL_NAME


def test_openrouter_provider_uses_its_own_environment_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = get_llm_config()

    assert config.provider == "openrouter"
    assert config.api_url == OPENROUTER_API_URL
    assert config.model == OPENROUTER_MODEL_NAME

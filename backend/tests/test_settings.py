from __future__ import annotations

from app.core.settings import Settings


def test_settings_load_required_service_configuration(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/rag")
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("OPENAI_API_KEY", "provider-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:latest")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text:latest")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://user:pass@localhost:5432/rag"
    assert settings.github_token == "github-token"
    assert settings.llm_model == "llama3.1:latest"
    assert settings.embedding_model == "nomic-embed-text:latest"

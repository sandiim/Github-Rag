"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Settings required by the local application services."""

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://github_rag:github_rag_dev_password@localhost:5432/github_rag"
    github_token: str
    openai_api_key: str
    openai_base_url: str
    llm_model: str
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text:latest"

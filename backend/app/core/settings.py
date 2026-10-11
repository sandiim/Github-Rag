"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings required by the local application services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    github_token: str
    openai_api_key: str
    openai_base_url: str
    llm_model: str
    ollama_base_url: str
    embedding_model: str

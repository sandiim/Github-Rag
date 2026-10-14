"""FastAPI dependency wiring for application services."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.persistence.session import create_session_factory
from app.rag.ollama import EmbeddingClient
from app.rag.completion import CompletionClient
from app.rag.retrieval import RetrievalService
from app.services.chat import ChatService
from app.services.chat_stream import StreamingChatService
from app.services.repositories import RepositoryService


def get_session() -> Generator[Session, None, None]:
    settings = Settings()
    session = create_session_factory(settings.database_url)()
    try:
        yield session
    finally:
        session.close()


def get_repository_service(session: Session = Depends(get_session)) -> RepositoryService:
    return RepositoryService(session)


def get_chat_service(session: Session = Depends(get_session)) -> ChatService:
    settings = Settings()
    embeddings = EmbeddingClient(settings.ollama_base_url, settings.embedding_model)
    retriever = RetrievalService(session, embeddings)
    completion = CompletionClient(settings.openai_base_url, settings.openai_api_key, settings.llm_model)
    return ChatService(session, retriever, completion)


def get_chat_stream_service() -> StreamingChatService:
    """Build a streamer that owns its session for the response lifetime."""

    settings = Settings()
    factory = create_session_factory(settings.database_url)
    embeddings = EmbeddingClient(settings.ollama_base_url, settings.embedding_model)
    completion = CompletionClient(
        settings.openai_base_url, settings.openai_api_key, settings.llm_model
    )
    return StreamingChatService(
        factory, lambda session: RetrievalService(session, embeddings), completion
    )

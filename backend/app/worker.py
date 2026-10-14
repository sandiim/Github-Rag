"""Run the single-concurrency ingestion worker: python -m app.worker."""

import logging
from time import sleep

from app.core.settings import Settings
from app.github.client import GitHubClient
from app.persistence.jobs import JobStore
from app.persistence.session import create_session_factory
from app.rag.ollama import EmbeddingClient
from app.services.ingestion import IngestionRunner


def main() -> None:
    settings = Settings()
    sessions = create_session_factory(settings.database_url)
    runner = IngestionRunner(
        sessions,
        GitHubClient(settings.github_token),
        EmbeddingClient(settings.ollama_base_url, settings.embedding_model),
        JobStore(sessions),
    )
    logging.basicConfig(level=logging.INFO)
    logging.info("Ingestion worker started")
    try:
        while True:
            if not runner.run_once():
                sleep(2)
    except KeyboardInterrupt:
        logging.info("Ingestion worker stopped")


if __name__ == "__main__":
    main()

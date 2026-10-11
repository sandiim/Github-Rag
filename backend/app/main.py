"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.routes import router


def create_app() -> FastAPI:
    """Create the HTTP application without initializing external services."""

    app = FastAPI(title="GitHub Repository RAG")
    app.include_router(router)
    return app


app = create_app()

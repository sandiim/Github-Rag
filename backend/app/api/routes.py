"""Routes that do not belong to a domain feature yet."""

from fastapi import APIRouter

from app.api.repositories import router as repositories_router

router = APIRouter()
router.include_router(repositories_router)


@router.get("/health")
def health() -> dict[str, str]:
    """Report whether the HTTP application is running."""

    return {"status": "ok"}

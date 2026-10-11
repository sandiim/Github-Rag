"""Routes that do not belong to a domain feature yet."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Report whether the HTTP application is running."""

    return {"status": "ok"}

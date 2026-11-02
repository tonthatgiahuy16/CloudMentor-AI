from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.database import engine
from app.core.logger import logger


router = APIRouter(tags=["Health"])


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_chroma_connection() -> None:
    from app.rag.vector_store import VectorStore

    VectorStore()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe: the process can accept HTTP requests."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    """Readiness probe: PostgreSQL and the derived Chroma index are usable."""
    try:
        check_database_connection()
        check_chroma_connection()
    except Exception as exc:
        logger.exception("Readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencies are not ready",
        ) from exc

    return {"status": "ready"}

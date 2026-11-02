from fastapi import HTTPException, status

from app.core import config


def require_mutations_enabled() -> None:
    """Block state-changing routes while serving the public demo."""
    if config.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode does not allow data changes",
        )

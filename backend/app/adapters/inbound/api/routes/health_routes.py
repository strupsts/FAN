from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.infrastructure.database import check_database_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", response_model=None)
def database_health_check() -> dict[str, str] | JSONResponse:
    if check_database_connection():
        return {
            "status": "ok",
            "database": "ok",
        }

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "error",
            "database": "unavailable",
        },
    )

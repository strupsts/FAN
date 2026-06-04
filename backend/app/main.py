from __future__ import annotations

from fastapi import FastAPI

from app.adapters.inbound.api.routes.health_routes import router as health_router
from app.adapters.inbound.api.routes.receipt_routes import router as receipt_router


def create_app() -> FastAPI:
    app = FastAPI(title="F.A.N. API")

    app.include_router(health_router)
    app.include_router(receipt_router)

    return app


app = create_app()

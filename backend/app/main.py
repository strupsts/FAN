from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.api.routes.health_routes import (
    router as health_router,
)
from app.adapters.inbound.api.routes.receipt_routes import (
    router as receipt_router,
)
from app.adapters.inbound.api.routes.user_routes import (
    router as user_router,
)


LOCAL_APP_ORIGINS = [
    "http://localhost",
    "https://localhost",
    "capacitor://localhost",
]


def create_app() -> FastAPI:
    app = FastAPI(title="F.A.N. API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_APP_ORIGINS,
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "OPTIONS",
        ],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(receipt_router)
    app.include_router(user_router)

    return app


app = create_app()

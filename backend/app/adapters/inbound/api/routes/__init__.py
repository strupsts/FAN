from app.adapters.inbound.api.routes.health_routes import router as health_router
from app.adapters.inbound.api.routes.receipt_routes import router as receipt_router

__all__ = [
    "health_router",
    "receipt_router",
]

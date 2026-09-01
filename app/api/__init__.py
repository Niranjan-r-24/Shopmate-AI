from fastapi import APIRouter
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.product_routes import router as product_router
from app.api.order_routes import router as order_router
from app.api.rag_routes import router as rag_router
from app.api.memory_routes import router as memory_router
from app.api.analytics_routes import router as analytics_router
from app.api.tool_routes import router as tool_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(product_router)
api_router.include_router(order_router)
api_router.include_router(rag_router)
api_router.include_router(memory_router)
api_router.include_router(analytics_router)
api_router.include_router(tool_router)

__all__ = ["api_router"]

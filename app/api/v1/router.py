from fastapi import APIRouter

from app.api.v1.routes.analysis import router as analysis_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.review import router as review_router
from app.api.v1.routes.thesis import router as thesis_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(thesis_router)
v1_router.include_router(analysis_router)
v1_router.include_router(chat_router)
v1_router.include_router(review_router, prefix="/review", tags=["Review"])
v1_router.include_router(health_router)  # GET /api/v1/health/ai

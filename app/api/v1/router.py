from fastapi import APIRouter

from app.api.v1.routes.analysis import router as analysis_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.review import router as review_router
from app.api.v1.routes.thesis import router as thesis_router

# Router principal
v1_router = APIRouter()  # NO pongas prefix aquí

# Incluir routers con sus propios prefijos
v1_router.include_router(thesis_router, prefix="/thesis")
v1_router.include_router(analysis_router, prefix="/analysis")
v1_router.include_router(chat_router, prefix="/chat")
v1_router.include_router(review_router, prefix="/review")
v1_router.include_router(health_router, prefix="/health")
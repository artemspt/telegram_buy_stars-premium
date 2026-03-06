from fastapi import APIRouter

from src.premium.endpoints import router as premium_router
from src.stars.endpoints import router as stars_router

router = APIRouter(prefix="/v1")

router.include_router(stars_router)
router.include_router(premium_router)

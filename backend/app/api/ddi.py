from functools import lru_cache

from fastapi import APIRouter

from app.models.schemas import DDICheckRequest, DDICheckResponse
from app.services.ddi_service import DDIService

router = APIRouter(prefix="/api/ddi", tags=["DDI"])


@lru_cache(maxsize=1)
def get_ddi_service() -> DDIService:
    return DDIService()


@router.post("/check", response_model=DDICheckResponse)
def check_ddi(payload: DDICheckRequest):
    return get_ddi_service().check(
        medicine_names=payload.medicines,
        use_gnn_fallback=payload.use_gnn_fallback,
    )

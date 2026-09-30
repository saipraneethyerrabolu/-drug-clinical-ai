from functools import lru_cache
from fastapi import APIRouter, Query

from app.models.schemas import MedicineSearchItem, ResolveMedicineRequest, MedicineResolutionResponse
from app.services.medicine_mapping_service import MedicineMappingService

router = APIRouter(prefix="/api/medicines", tags=["Medicines"])


@lru_cache(maxsize=1)
def get_service() -> MedicineMappingService:
    return MedicineMappingService()


@router.get("/search", response_model=list[MedicineSearchItem])
def search_medicines(q: str = Query(min_length=1), limit: int = Query(default=10, ge=1, le=50)):
    return get_service().search(q, limit)


@router.post("/resolve", response_model=MedicineResolutionResponse)
def resolve_medicine(payload: ResolveMedicineRequest):
    return get_service().resolve(payload.medicine_name)

from fastapi import APIRouter, Query

from app.models.schemas import (
    MedicineSearchItem,
    ResolveMedicineRequest,
    MedicineResolutionResponse,
)
from app.services.medicine_mapping_service import get_mapping_service

router = APIRouter(prefix="/api/medicines", tags=["Medicines"])


@router.get("/search", response_model=list[MedicineSearchItem])
def search_medicines(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    return get_mapping_service().search(q, limit)


@router.post("/resolve", response_model=MedicineResolutionResponse)
def resolve_medicine(payload: ResolveMedicineRequest):
    return get_mapping_service().resolve(payload.medicine_name)
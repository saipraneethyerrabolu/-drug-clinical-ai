from fastapi import APIRouter

from app.models.schemas import AlternativeRecommendRequest, AlternativeRecommendResponse
from app.services.alternative_service import AlternativeService

router = APIRouter(prefix="/api/alternatives", tags=["Alternatives"])
_service: AlternativeService | None = None


def get_service() -> AlternativeService:
    global _service
    if _service is None:
        _service = AlternativeService()
    return _service


@router.post("/recommend", response_model=AlternativeRecommendResponse)
def recommend_alternatives(payload: AlternativeRecommendRequest):
    return get_service().recommend(
        medicine_name=payload.medicine_name,
        other_medicines=payload.other_medicines,
        max_alternatives=payload.max_alternatives,
        use_gnn_fallback=payload.use_gnn_fallback,
    )

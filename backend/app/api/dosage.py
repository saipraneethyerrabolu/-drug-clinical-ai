from functools import lru_cache
from fastapi import APIRouter, Query

from app.models.schemas import (
    DosageCheckRequest,
    DosageCheckResponse,
    OfficialLabelReferenceResponse,
)
from app.services.dosage_service import DosageService
from app.services.official_label_service import OfficialLabelService

router = APIRouter(prefix="/api/dosage", tags=["Dosage"])


@lru_cache(maxsize=1)
def get_dosage_service() -> DosageService:
    return DosageService()


@lru_cache(maxsize=1)
def get_official_label_service() -> OfficialLabelService:
    return OfficialLabelService()


@router.post("/check", response_model=DosageCheckResponse)
def check_dosage(request: DosageCheckRequest):
    return get_dosage_service().check(
        medicine_name=request.medicine_name,
        age_years=request.age_years,
        weight_kg=request.weight_kg,
        disease=request.disease,
        route=request.route,
        crcl_ml_min=request.crcl_ml_min,
    )


@router.get("/official-label", response_model=OfficialLabelReferenceResponse)
def official_label_reference(
    medicine_name: str = Query(min_length=1, description="Resolved generic medicine name preferred"),
):
    """Fetch reference metadata and label text from the official openFDA label API.

    Includes the Dosage and Administration section as published on the
    official FDA label (verbatim reference text, not a personalized
    recommendation from this system's own dosage model).
    """
    return get_official_label_service().lookup(medicine_name)
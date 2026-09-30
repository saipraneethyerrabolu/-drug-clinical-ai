from fastapi import APIRouter

from app.models.schemas import ClinicalAnalyzeRequest, ClinicalAnalyzeResponse
from app.services.clinical_service import ClinicalService

router = APIRouter(prefix="/api/clinical", tags=["Clinical Integration"])
_service: ClinicalService | None = None


def get_service() -> ClinicalService:
    global _service
    if _service is None:
        _service = ClinicalService()
    return _service


@router.post("/analyze", response_model=ClinicalAnalyzeResponse)
def analyze_clinical(payload: ClinicalAnalyzeRequest):
    return get_service().analyze(
        medicines=payload.medicines,
        age_years=payload.age_years,
        weight_kg=payload.weight_kg,
        disease=payload.disease,
        route=payload.route,
        crcl_ml_min=payload.crcl_ml_min,
        gene_symbol=payload.gene_symbol or "TPMT",
        variants=payload.variants,
        use_gnn_fallback=payload.use_gnn_fallback,
        include_alternatives=payload.include_alternatives,
        max_alternative_sources=payload.max_alternative_sources,
        max_alternatives_per_medicine=payload.max_alternatives_per_medicine,
    )

from fastapi import APIRouter

from app.models.schemas import PGxCheckRequest, PGxCheckResponse
from app.services.pgx_service import PGxService

router = APIRouter(prefix="/api/pgx", tags=["PGx"])
_service: PGxService | None = None


def get_service() -> PGxService:
    global _service
    if _service is None:
        _service = PGxService()
    return _service


@router.post("/check", response_model=PGxCheckResponse)
def check_pgx(req: PGxCheckRequest):
    return get_service().check(req.medicine_name, req.gene_symbol, req.variants)

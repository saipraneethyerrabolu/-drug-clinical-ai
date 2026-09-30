from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ddi import router as ddi_router
from app.api.medicines import router as medicines_router
from app.api.dosage import router as dosage_router
from app.api.pgx import router as pgx_router
from app.api.alternatives import router as alternatives_router
from app.api.clinical import router as clinical_router

app = FastAPI(
    title="AI Drug Clinical Decision Support API",
    version="0.9.0",
    description=(
        "Phase 9: integrated clinical backend, React/Vite frontend, and official FDA label reference fallback."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(medicines_router)
app.include_router(ddi_router)
app.include_router(dosage_router)
app.include_router(pgx_router)
app.include_router(alternatives_router)
app.include_router(clinical_router)


@app.get("/")
def root():
    return {"status": "ok", "phase": "Phase 9", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy", "phase": "Phase 9"}

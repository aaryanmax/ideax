from fastapi import APIRouter
from app.api.v1.endpoints import audit
from app.api.v1.endpoints import ingest

try:
    from app.api.v1.endpoints import search
except ImportError:
    from app.engine import search

try:
    from app.api.v1.endpoints import search
except ImportError:
    from app.engine import search


try:
    from app.api.v1.endpoints import analyze
except ImportError:
    from app.engine import analyze

from app.api.v1.endpoints import dataset_studio

router = APIRouter()

@router.get("/status")
def status():
    return {"status": "ok"}

# Mount all feature streams
router.include_router(search.router, prefix="/search", tags=["Semantic Search"])
router.include_router(analyze.router, prefix="/analyze", tags=["Bitemporal Change & Tactical Classification"])
router.include_router(audit.router, prefix="/audit", tags=["Audit & Target Commitment"])
router.include_router(ingest.router, prefix="/ingest", tags=["Incremental Ingest"])
router.include_router(dataset_studio.router, prefix="/dataset-studio", tags=["Dataset Studio"])

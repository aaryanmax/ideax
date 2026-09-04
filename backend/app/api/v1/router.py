from fastapi import APIRouter
from app.api.v1.endpoints import search, change, audit

router = APIRouter()

@router.get("/status")
def status():
    return {"status": "ok"}

router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(change.router, prefix="/analyze/change", tags=["change"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])

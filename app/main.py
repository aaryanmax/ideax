"""
FastAPI entry point for VAYU.
Run: uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import HOST, PORT
from app.api import routes

app = FastAPI(
    title="VAYU — Semantic Satellite Search & Change Detection",
    description="Offline semantic retrieval + temporal change detection for Earth Observation",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["127.0.0.1", "localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router)


@app.on_event("startup")
async def startup_event():
    """Initialize vector index and clusterer at server startup."""
    print("[VAYU] Initializing backend...")
    routes.init_vector_index()
    print("[VAYU] Backend ready. Listening on http://127.0.0.1:8000")


@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
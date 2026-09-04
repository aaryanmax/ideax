import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import router as v1_router

app = FastAPI(title="VAYU-CHRONICLE Core", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve path to data directory and mount static file serving for tiles
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "processed"))
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/static/tiles", StaticFiles(directory=DATA_DIR), name="tiles")

app.include_router(v1_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "VAYU-CHRONICLE Core Online"}

if __name__ == "__main__":
    uvicorn.run("run_server:app", host="0.0.0.0", port=8000, reload=True)

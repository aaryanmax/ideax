from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import sys

from app.engine.embedder import Embedder
from app.engine.vector_index import VectorIndexManager
from app.engine.search import SemanticSearchEngine

router = APIRouter()

# Global Singleton initialization
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

index_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_delhi.index")
metadata_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_metadata.json")

print("[*] Initializing SemanticSearchEngine Singleton...")
embedder = Embedder()
index_manager = VectorIndexManager(dim=768)

if os.path.exists(index_path):
    index_manager.load(index_path)
    
search_engine = SemanticSearchEngine(embedder, index_manager, metadata_path)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/text")
def search_text(request: SearchRequest):
    try:
        results = search_engine.search_by_text(request.query, top_k=request.top_k)
        return {
            "type": "FeatureCollection",
            "features": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

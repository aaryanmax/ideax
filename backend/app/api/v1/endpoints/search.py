from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import sys

from app.engine.embedder import Embedder
from app.engine.vector_index import VectorIndexManager
from app.engine.search import SemanticSearchEngine
from app.engine.clustering import cluster_geospatial_features
from app.models.schemas import SimilarSearchRequest, DiscoveryResponse

router = APIRouter()

# Global Singleton initialization
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

# Load both Delhi and Mumbai datasets
delhi_index_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_delhi.index")
delhi_metadata_path = os.path.join(PROJECT_ROOT, "data", "processed", "test_metadata.json")

mumbai_index_path = os.path.join(PROJECT_ROOT, "data", "processed", "satellite_tiles.index")
mumbai_metadata_path = os.path.join(PROJECT_ROOT, "data", "processed", "mumbai_metadata.json")

embedder = Embedder()

print("[*] Initializing SemanticSearchEngines for Unified Search...")
delhi_engine = None
if os.path.exists(delhi_index_path) and os.path.exists(delhi_metadata_path):
    idx_delhi = VectorIndexManager(dim=768)
    idx_delhi.load(delhi_index_path)
    delhi_engine = SemanticSearchEngine(embedder, idx_delhi, delhi_metadata_path)

mumbai_engine = None
if os.path.exists(mumbai_index_path) and os.path.exists(mumbai_metadata_path):
    idx_mumbai = VectorIndexManager(dim=768)
    idx_mumbai.load(mumbai_index_path)
    mumbai_engine = SemanticSearchEngine(embedder, idx_mumbai, mumbai_metadata_path)

# Fallback alias for endpoints that use `search_engine` directly (e.g. similar search)
search_engine = mumbai_engine if mumbai_engine else delhi_engine

from typing import Optional

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    dataset: Optional[str] = "all"  # "all", "delhi", "mumbai"

@router.post("/text")
def search_text(request: SearchRequest):
    try:
        dataset_filter = request.dataset.lower() if request.dataset else "all"
        
        if dataset_filter == "all" and delhi_engine and mumbai_engine:
            res_delhi = delhi_engine.search_by_text(request.query, top_k=request.top_k)
            res_mumbai = mumbai_engine.search_by_text(request.query, top_k=request.top_k)
            # Interleave equally
            combined_results = []
            for i in range(max(len(res_delhi), len(res_mumbai))):
                if i < len(res_delhi):
                    combined_results.append(res_delhi[i])
                if i < len(res_mumbai):
                    combined_results.append(res_mumbai[i])
            top_results = combined_results[:request.top_k]
        else:
            combined_results = []
            if delhi_engine and dataset_filter in ["all", "delhi"]:
                combined_results.extend(delhi_engine.search_by_text(request.query, top_k=request.top_k))
            if mumbai_engine and dataset_filter in ["all", "mumbai"]:
                combined_results.extend(mumbai_engine.search_by_text(request.query, top_k=request.top_k))
                
            combined_results.sort(key=lambda x: x["properties"]["similarity_score"])
            top_results = combined_results[:request.top_k]
        
        return {
            "type": "FeatureCollection",
            "features": top_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/similar", response_model=DiscoveryResponse)
def search_similar(request: SimilarSearchRequest):
    try:
        # Get raw similarity features
        features = search_engine.find_similar_by_patch_id(
            patch_id=request.patch_id, 
            top_k=request.top_k
        )
        
        # Optionally cluster them
        clusters = []
        if request.cluster_results and features:
            cluster_data = cluster_geospatial_features(
                features, 
                eps_km=request.eps_km, 
                min_samples=request.min_samples
            )
            features = cluster_data["features"]
            clusters = cluster_data["clusters"]
            
        # Formulate tactical summary
        named_clusters = sum(1 for c in clusters if c["cluster_id"] != -1)
        summary = f"DISCOVERY SWEEP COMPLETE: Identified {len(features)} semantically aligned sites matching baseline signature '{request.patch_id}'. Grouped into {named_clusters} operational activity clusters across Delhi AOR."
        
        return DiscoveryResponse(
            source_patch_id=request.patch_id,
            total_matches=len(features),
            features=features,
            clusters=clusters,
            tactical_summary=summary
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

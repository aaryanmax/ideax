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

embedder = Embedder()

print("[*] Initializing SearchEngineManager for Unified Search...")
from app.engine.search import SearchEngineManager
engine_manager = SearchEngineManager(embedder)

from typing import Optional

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    dataset: Optional[str] = "all"

@router.get("/datasets")
def get_datasets():
    datasets = list(engine_manager.engines.keys())
    options = [{"value": "none", "label": "Auto (Map View)"}, {"value": "all", "label": "All Datasets"}]
    for ds in datasets:
        options.append({"value": ds, "label": ds.replace("_", " ").title()})
    return {"datasets": options}

@router.post("/text")
def search_text(request: SearchRequest):
    try:
        dataset_filter = request.dataset.lower() if request.dataset else "all"
        if dataset_filter in ["all", "none", "auto"]:
            dataset_filter = "all"
        
        combined_results = []
        
        if dataset_filter == "all":
            all_results = []
            for name, engine in engine_manager.engines.items():
                all_results.append(engine.search_by_text(request.query, top_k=request.top_k))
            
            max_len = max([len(res) for res in all_results]) if all_results else 0
            for i in range(max_len):
                for res in all_results:
                    if i < len(res):
                        combined_results.append(res[i])
        else:
            engine = engine_manager.get_engine(dataset_filter)
            if engine:
                combined_results.extend(engine.search_by_text(request.query, top_k=request.top_k))
                
        combined_results.sort(key=lambda x: x["properties"]["similarity_score"], reverse=True)
        top_results = combined_results[:request.top_k]
        
        return {
            "type": "FeatureCollection",
            "features": top_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        with open("search_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/similar", response_model=DiscoveryResponse)
def search_similar(request: SimilarSearchRequest):
    try:
        # Dynamically find the dataset that contains this patch_id
        search_engine = None
        dataset_name = None
        
        # Fast lookup
        for name, engine in engine_manager.engines.items():
            if request.patch_id in engine.metadata:
                search_engine = engine
                dataset_name = name
                break
                
        # Deep lookup in case of unstructured metadata
        if not search_engine:
            for name, engine in engine_manager.engines.items():
                if isinstance(engine.metadata, dict):
                    if any(v.get("patch_id") == request.patch_id for v in engine.metadata.values()):
                        search_engine = engine
                        dataset_name = name
                        break
                elif isinstance(engine.metadata, list):
                    if any(v.get("patch_id") == request.patch_id for v in engine.metadata):
                        search_engine = engine
                        dataset_name = name
                        break

        if not search_engine:
            raise ValueError(f"Patch ID {request.patch_id} not found in any available datasets.")
            
        features = search_engine.find_similar_by_patch_id(
            patch_id=request.patch_id, 
            top_k=request.top_k
        )
        
        clusters = []
        if request.cluster_results and features:
            cluster_data = cluster_geospatial_features(
                features, 
                eps_km=request.eps_km, 
                min_samples=request.min_samples
            )
            features = cluster_data["features"]
            clusters = cluster_data["clusters"]
            
        named_clusters = sum(1 for c in clusters if c["cluster_id"] != -1)
        aor = dataset_name.replace("_", " ").title()
        summary = f"DISCOVERY SWEEP COMPLETE: Identified {len(features)} semantically aligned sites matching baseline signature '{request.patch_id}'. Grouped into {named_clusters} operational activity clusters across {aor} AOR."
        
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

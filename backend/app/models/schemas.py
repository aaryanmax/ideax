"""
REST endpoints for semantic search, change detection, clustering.
Real data integration: loads K's/Yash's FAISS index + metadata.
"""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from app.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    ChangeDetectionRequest,
    ClusterRequest,
)
from app.engine.vector_index import VectorIndex
from app.engine.clustering import TileClusterer
from app.config import FAISS_INDEX_PATH, METADATA_PATH, EMBEDDINGS_PATH
import numpy as np
import time

router = APIRouter(prefix="/api/v1", tags=["search"])
vector_index = None  # Loaded once at app startup
clusterer = None


def init_vector_index():
    """Call this from app.main.py at startup."""
    global vector_index, clusterer
    
    try:
        vector_index = VectorIndex(
            str(FAISS_INDEX_PATH),
            str(METADATA_PATH),
            str(EMBEDDINGS_PATH),
        )
        print(f"[routes] VectorIndex initialized with {vector_index.ntotal} tiles")
        
        # Initialize clusterer (uses embeddings from vector_index)
        clusterer = TileClusterer(vector_index)
        print(f"[routes] Clusterer initialized")
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize vector index: {e}")
        raise


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Semantic search over satellite tiles.
    Text query → CLIP encoder → FAISS top-k.
    
    Currently uses dummy encoding (hash-based).
    TODO: Replace with A's real CLIP text tower.
    """
    if vector_index is None:
        raise HTTPException(status_code=500, detail="Vector index not initialized")
    
    # PLACEHOLDER: dummy encoding from query string hash
    # This will be replaced with A's real text encoder API call
    import hashlib
    seed = int(hashlib.md5(req.query.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    query_vec = rng.random(512).astype("float32")
    query_vec = query_vec / np.linalg.norm(query_vec)
    
    start = time.perf_counter()
    try:
        results, search_time_ms = vector_index.search(
            query_vec,
            top_k=req.top_k,
            date_range_start=req.date_range_start,
            date_range_end=req.date_range_end,
            sensor_filter=req.sensor_filter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    total_time_ms = (time.perf_counter() - start) * 1000
    
    return SearchResponse(
        query=req.query,
        top_k=req.top_k,
        n_results=len(results),
        results=results,
        execution_time_ms=total_time_ms,
    )


@router.post("/cluster")
def cluster_discovery(req: ClusterRequest):
    """
    Find tiles semantically similar to a seed tile.
    Uses embedding-space KNN (fast, no training needed).
    """
    if clusterer is None:
        raise HTTPException(status_code=500, detail="Clusterer not initialized")
    
    try:
        results = clusterer.find_similar_tiles(
            req.tile_id,
            top_k=req.top_k,
            distance_threshold=0.4,  # cosine distance
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"Tile not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")
    
    return {
        "seed_tile_id": req.tile_id,
        "n_results": len(results),
        "similar_tiles": results,
    }


@router.post("/change")
def change_detection(req: ChangeDetectionRequest):
    """
    Compare two tiles at different timestamps.
    Calls A's SFAS gate and returns change mask + confidence.
    
    TODO: Integrate with A's change detection module.
    For now, returns a placeholder using cosine distance between embeddings.
    """
    if vector_index is None:
        raise HTTPException(status_code=500, detail="Vector index not initialized")
    
    try:
        # Find both tiles
        t1_idx = None
        t2_idx = None
        for tile in vector_index.tiles:
            if tile.tile_id == req.tile_id_t1:
                t1_idx = tile.embedding_index
            if tile.tile_id == req.tile_id_t2:
                t2_idx = tile.embedding_index
        
        if t1_idx is None or t2_idx is None:
            raise ValueError(f"One or both tiles not found: {req.tile_id_t1}, {req.tile_id_t2}")
        
        # Get embeddings
        emb_t1 = vector_index.get_embedding(t1_idx)
        emb_t2 = vector_index.get_embedding(t2_idx)
        
        # Cosine similarity + change score
        cosine_sim = float(np.dot(emb_t1, emb_t2))
        change_score = 1.0 - cosine_sim  # 0 = identical, 1 = totally different
        
        return {
            "tile_id_t1": req.tile_id_t1,
            "tile_id_t2": req.tile_id_t2,
            "cosine_similarity": cosine_sim,
            "change_score": change_score,
            "status": "awaiting_sfas_gate",
            "message": "Change score computed from embeddings. Full detection mask pending A's SFAS implementation.",
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Change detection failed: {str(e)}")
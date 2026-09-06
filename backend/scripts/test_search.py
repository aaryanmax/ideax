import sys
import os
import time
import numpy as np
from PIL import Image
import rasterio
from rasterio.windows import Window
import json

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.engine.embedder import Embedder
from app.engine.vector_index import VectorIndexManager
from app.engine.search import SemanticSearchEngine
from scripts.test_engine import extract_patch_and_bounds

def main():
    jp2_path = os.path.join(PROJECT_ROOT, "data", "processed", "T43RFM_20260831T052641_TCI_10m.jp2")
    if not os.path.exists(jp2_path):
        print(f"[ERROR] JP2 file not found at: {jp2_path}")
        sys.exit(1)
        
    index_path = os.path.join(PROJECT_ROOT, "data", "processed", "delhi.index")
    metadata_path = os.path.join(PROJECT_ROOT, "data", "processed", "delhi_metadata.json")
    
    print("[*] Initializing Foundation Model Embedder...")
    embedder = Embedder()
    
    print("[*] Generating 20 spatial crops and their embeddings...")
    index_manager = VectorIndexManager(dim=768)
    search_engine = SemanticSearchEngine(embedder, index_manager)
    
    patch_size = 512
    # Create a 4x5 grid starting at col=4000, row=4000
    start_col, start_row = 4000, 4000
    
    embeddings = []
    
    with rasterio.open(jp2_path) as src:
        max_width = src.width
        max_height = src.height
        
    for i in range(20):
        grid_x = i % 5
        grid_y = i // 5
        col = start_col + grid_x * patch_size
        row = start_row + grid_y * patch_size
        
        # Ensure within bounds
        if col + patch_size > max_width or row + patch_size > max_height:
            continue
            
        window = Window(col, row, patch_size, patch_size)
        patch_arr, bounds_geo = extract_patch_and_bounds(jp2_path, window)
        
        pil_img = Image.fromarray(patch_arr)
        emb = embedder.embed_image(pil_img)
        embeddings.append(emb)
        
        search_engine.metadata[str(i)] = {
            "patch_id": f"patch_{i}",
            "bounds": [bounds_geo["min_lat"], bounds_geo["min_lon"], bounds_geo["max_lat"], bounds_geo["max_lon"]],
            "center": [(bounds_geo["min_lat"] + bounds_geo["max_lat"]) / 2, (bounds_geo["min_lon"] + bounds_geo["max_lon"]) / 2],
            "file_path": jp2_path
        }
        
    print("[*] Adding embeddings to FAISS HNSW flat index...")
    embeddings_np = np.array(embeddings)
    index_manager.add_vectors(embeddings_np)
    
    print(f"[*] Saving index to {os.path.basename(index_path)} and metadata to {os.path.basename(metadata_path)}...")
    index_manager.save(index_path)
    search_engine.save_metadata(metadata_path)
    
    # Executing 3 verification queries
    queries = [
        "dense urban settlement or buildings",
        "seasonal crop fields or agricultural land",
        "water body or riverbed"
    ]
    
    print("\n" + "=" * 80)
    print("                FAISS VECTOR SEARCH RETRIEVAL VERIFICATION")
    print("=" * 80)
    
    for query in queries:
        print(f"\n[QUERY]: '{query}'")
        
        t_embed_start = time.perf_counter()
        query_emb = embedder.embed_text(query)
        t_embed = (time.perf_counter() - t_embed_start) * 1000
        
        t_faiss_start = time.perf_counter()
        distances, indices = index_manager.search(query_emb, top_k=3)
        t_faiss = (time.perf_counter() - t_faiss_start) * 1000
        
        t_resolve_start = time.perf_counter()
        # The search_engine.search_by_text also computes embed and FAISS search inside, 
        # so we will use it directly to measure total retrieval time.
        results = search_engine.search_by_text(query, top_k=3)
        t_total = (time.perf_counter() - t_resolve_start) * 1000
        
        for idx, res in enumerate(results):
            score = res['properties']['similarity_score']
            center = res['properties']['center']
            patch_id = res['properties']['patch_id']
            print(f"    - Rank {idx+1}: {patch_id:8s} | Similarity: {score:.4f} | Center Lat/Lon: {center[0]:.6f}, {center[1]:.6f}")
            
        print(f"  [BENCHMARK] Embed Latency: {t_embed:.2f} ms | FAISS Search: {t_faiss:.2f} ms | Total Retrieval (End-to-End): {t_total:.2f} ms")
        
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()

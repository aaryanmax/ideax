# test_integration.py
import sys
from pathlib import Path
from app.config import FAISS_INDEX_PATH, METADATA_PATH, EMBEDDINGS_PATH
from app.engine.vector_index import VectorIndex
from app.engine.clustering import TileClusterer
import numpy as np

def test_vector_index():
    print("[TEST] Loading VectorIndex...")
    try:
        vi = VectorIndex(
            str(FAISS_INDEX_PATH),
            str(METADATA_PATH),
            str(EMBEDDINGS_PATH),
        )
        print(f"  ✓ Loaded {vi.ntotal} tiles")
        return vi
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_search(vi):
    print("[TEST] Searching with random query vector...")
    try:
        query = np.random.randn(512).astype('float32')
        query = query / np.linalg.norm(query)
        
        results, latency_ms = vi.search(query, top_k=5)
        print(f"  ✓ Got {len(results)} results in {latency_ms:.2f}ms")
        if results:
            print(f"    Top result: {results[0].tile_id} (score={results[0].score:.4f})")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_clustering(vi):
    print("[TEST] Clustering...")
    try:
        clusterer = TileClusterer(vi)
        if len(vi.tiles) > 0:
            seed = vi.tiles[0].tile_id
            similar = clusterer.find_similar_tiles(seed, top_k=5)
            print(f"  ✓ Found {len(similar)} tiles similar to {seed}")
            if similar:
                print(f"    Closest: {similar[0]['tile_id']} (distance={similar[0]['distance']:.4f})")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("=== VAYU Integration Test ===\n")
    vi = test_vector_index()
    test_search(vi)
    test_clustering(vi)
    print("\n✓ All integration tests passed!")
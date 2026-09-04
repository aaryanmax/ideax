import json
import os
from typing import List, Dict

class SemanticSearchEngine:
    def __init__(self, embedder, index_manager, metadata_path: str = None):
        self.embedder = embedder
        self.index_manager = index_manager
        self.metadata = {}
        if metadata_path and os.path.exists(metadata_path):
            self.load_metadata(metadata_path)
            
    def load_metadata(self, metadata_path: str):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
            
    def save_metadata(self, metadata_path: str):
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=4)
            
    def search_by_text(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        1. Encodes text via embedder.embed_text(query).
        2. Runs HNSW vector search.
        3. Resolves and returns top records formatted as GeoJSON-compatible dictionaries with similarity scores.
        """
        if self.index_manager.index.ntotal == 0:
            return []
            
        # 1. Encode text
        query_embedding = self.embedder.embed_text(query)
        
        # 2. Vector search
        distances, indices = self.index_manager.search(query_embedding, top_k=top_k)
        
        # 3. Resolve metadata
        results = []
        # FAISS search returns a 2D array: (1, top_k)
        # distances are similarities because we use inner product with normalized vectors
        for score, idx in zip(distances[0], indices[0]):
            idx_str = str(idx) # JSON keys are always strings
            if idx_str in self.metadata:
                record = self.metadata[idx_str]
                
                # Format as GeoJSON-compatible Feature
                # bounds: [min_lat, min_lon, max_lat, max_lon]
                min_lat, min_lon, max_lat, max_lon = record["bounds"]
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [min_lon, max_lat], # Top-left
                            [max_lon, max_lat], # Top-right
                            [max_lon, min_lat], # Bottom-right
                            [min_lon, min_lat], # Bottom-left
                            [min_lon, max_lat]  # Close polygon
                        ]]
                    },
                    "properties": {
                        "patch_id": record.get("patch_id", idx_str),
                        "similarity_score": float(score),
                        "center": record.get("center"),
                        "file_path": record.get("file_path"),
                        "thumbnail_url": record.get("thumbnail_url"),
                        "col_off": record.get("col_off"),
                        "row_off": record.get("row_off")
                    }
                }
                results.append(feature)
        
        return results
